import torch
from torch import nn

class CRF(nn.Module):
    """
    Implements Conditional Random Fields that can be trained via
    backpropagation. 
    """
    def __init__(self, num_tags):
        super(CRF, self).__init__()
        
        self.num_tags = num_tags
        self.transitions = nn.Parameter(torch.Tensor(num_tags, num_tags))
        self.start_transitions = nn.Parameter(torch.randn(num_tags))
        self.stop_transitions = nn.Parameter(torch.randn(num_tags))

        nn.init.xavier_normal_(self.transitions)

    def forward(self, feats):
        # Shape checks
        if len(feats.shape) != 3:
            raise ValueError("feats must be 3-d got {}-d".format(feats.shape))

        return self._viterbi(feats)

    def loss(self, feats, tags):
        """
        Computes negative log likelihood between features and tags.
        Essentially difference between individual sequence scores and 
        sum of all possible sequence scores (partition function)
        Parameters:
            feats: Input features [batch size, sequence length, number of tags]
            tags: Target tag indices [batch size, sequence length]. Should be between
                    0 and num_tags
        Returns:
            Negative log likelihood [a scalar] 
        """
        # Shape checks
        if len(feats.shape) != 3:
            raise ValueError("feats must be 3-d got {}-d".format(feats.shape))

        if len(tags.shape) != 2:
            raise ValueError('tags must be 2-d but got {}-d'.format(tags.shape))

        if feats.shape[:2] != tags.shape:
            raise ValueError('First two dimensions of feats and tags must match ', feats.shape, tags.shape)

        sequence_score = self._sequence_score(feats, tags)
        partition_function = self._partition_function(feats)
        log_probability = sequence_score - partition_function

        # -ve of l()
        # Average across batch
        return -log_probability.mean()

    def _sequence_score(self, feats, tags):
        """
        Parameters:
            feats: Input features [batch size, sequence length, number of tags]
            tags: Target tag indices [batch size, sequence length]. Should be between
                    0 and num_tags
        Returns: Sequence score of shape [batch size]
        """

        batch_size = feats.shape[0]

        # Compute feature scores
        feat_score = feats.gather(2, tags.unsqueeze(-1)).squeeze(-1).sum(dim=-1)

        # print(feat_score.size())

        # Compute transition scores
        # Unfold to get [from, to] tag index pairs
        tags_pairs = tags.unfold(1, 2, 1)

        # Use advanced indexing to pull out required transition scores
        indices = tags_pairs.permute(2, 0, 1).chunk(2)
        trans_score = self.transitions[indices].squeeze(0).sum(dim=-1)

        # Compute start and stop scores
        start_score = self.start_transitions[tags[:, 0]]
        stop_score = self.stop_transitions[tags[:, -1]]

        return feat_score + start_score + trans_score + stop_score

    def _partition_function(self, feats):
        """
        Computes the partitition function for CRF using the forward algorithm.
        Basically calculate scores for all possible tag sequences for 
        the given feature vector sequence
        Parameters:
            feats: Input features [batch size, sequence length, number of tags]
        Returns:
            Total scores of shape [batch size]
        """
        _, seq_size, num_tags = feats.shape

        if self.num_tags != num_tags:
            raise ValueError('num_tags should be {} but got {}'.format(self.num_tags, num_tags))

        a = feats[:, 0] + self.start_transitions.unsqueeze(0) # [batch_size, num_tags]
        transitions = self.transitions.unsqueeze(0) # [1, num_tags, num_tags] from -> to

        for i in range(1, seq_size):
            feat = feats[:, i].unsqueeze(1) # [batch_size, 1, num_tags]
            a = self._log_sum_exp(a.unsqueeze(-1) + transitions + feat, 1) # [batch_size, num_tags]

        return self._log_sum_exp(a + self.stop_transitions.unsqueeze(0), 1) # [batch_size]

    def _viterbi(self, feats):
        """
        Uses Viterbi algorithm to predict the best sequence
        Parameters:
            feats: Input features [batch size, sequence length, number of tags]
        Returns: Best tag sequence [batch size, sequence length]
        """
        _, seq_size, num_tags = feats.shape

        if self.num_tags != num_tags:
            raise ValueError('num_tags should be {} but got {}'.format(self.num_tags, num_tags))
        
        v = feats[:, 0] + self.start_transitions.unsqueeze(0) # [batch_size, num_tags]
        transitions = self.transitions.unsqueeze(0) # [1, num_tags, num_tags] from -> to
        paths = []

        for i in range(1, seq_size):
            feat = feats[:, i] # [batch_size, num_tags]
            v, idx = (v.unsqueeze(-1) + transitions).max(1) # [batch_size, num_tags], [batch_size, num_tags]
            
            paths.append(idx)
            v = (v + feat) # [batch_size, num_tags]

        
        v, tag = (v + self.stop_transitions.unsqueeze(0)).max(1, True)

        # Backtrack
        tags = [tag]
        for idx in reversed(paths):
            tag = idx.gather(1, tag)
            tags.append(tag)

        tags.reverse()
        return torch.cat(tags, 1)

    
    def _log_sum_exp(self, logits, dim):
        """
        Computes log-sum-exp in a stable way
        """
        max_val, _ = logits.max(dim)
        return max_val + (logits - max_val.unsqueeze(dim)).exp().sum(dim).log()


def f1_score(preds, targets):
    '''
    어차피 val set 이나 test set 에서만 구할거라서 걍 리스트로 할거임
    input:
        pred: 2d-list
        target: 2d-list
        shape of both should be same
    '''
    assert type(preds) is list and type(targets) is list
    TP, FN, FP = 0, 0, 0
    for pred, true in zip(preds, targets):
        assert len(pred) == len(true)
        stpt = 0
        endpt = 0
        entity_flag = False
        neg_flag = False
        pred.append(0)
        true.append(0)

        # 1. find True Positive and False Negative
        for i in range(len(pred)):
            if true[i] != 0 and not entity_flag:
                stpt = i
                entity_flag = True

            if true[i] == 0 and entity_flag:
                endpt = i
                for comp_ind in range(stpt-1, endpt+1):
                    if true[comp_ind] != pred[comp_ind]:
                        neg_flag = True
                        break
                
                if neg_flag:
                    FN += 1
                else:
                    TP += 1
                entity_flag = False
                neg_flag = False
            
        # 2. find False Positive
        for i in range(len(pred)):
            if pred[i] == 1 and not entity_flag:
                stpt = i
                entity_flag = True

            if pred[i] == 0 and entity_flag:
                endpt = i
                for comp_ind in range(stpt-1, endpt+1):
                    if true[comp_ind] != pred[comp_ind]:
                        neg_flag = True
                        break
                
                if neg_flag:
                    FP += 1
                entity_flag = False
                neg_flag = False
                
    precision = TP/(TP + FP)
    recall = TP/(TP + FN)
    f1 = (2*precision*recall) / (precision + recall) if precision != 0 or recall != 0 else 0

    return f1