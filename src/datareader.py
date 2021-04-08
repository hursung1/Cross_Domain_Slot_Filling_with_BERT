
from preprocess.gen_embeddings_for_slu import slot_list

import numpy as np
import logging
logger = logging.getLogger()

y1_set = ["O", "B", "I"]
y2_set = ['O', 'B-playlist', 'I-playlist', 'B-music_item', 'I-music_item', 'B-geographic_poi', 'I-geographic_poi', 'B-facility', 'I-facility', 'B-movie_name', 'I-movie_name', 'B-location_name', 'I-location_name', 'B-restaurant_name', 'I-restaurant_name', 'B-track', 'I-track', 'B-restaurant_type', 'I-restaurant_type', 'B-object_part_of_series_type', 'I-object_part_of_series_type', 'B-country', 'I-country', 'B-service', 'I-service', 'B-poi', 'I-poi', 'B-party_size_description', 'I-party_size_description', 'B-served_dish', 'I-served_dish', 'B-genre',  'I-genre', 'B-current_location', 'I-current_location', 'B-object_select', 'I-object_select', 'B-album', 'I-album', 'B-object_name', 'I-object_name', 'B-state', 'I-state', 'B-sort', 'I-sort', 'B-object_location_type', 'I-object_location_type', 'B-movie_type', 'I-movie_type', 'B-spatial_relation', 'I-spatial_relation', 'B-artist', 'I-artist', 'B-cuisine', 'I-cuisine', 'B-entity_name', 'I-entity_name', 'B-object_type', 'I-object_type', 'B-playlist_owner', 'I-playlist_owner', 'B-timeRange', 'I-timeRange', 'B-city', 'I-city', 'B-rating_value', 'B-best_rating', 'B-rating_unit', 'B-year', 'B-party_size_number', 'B-condition_description', 'B-condition_temperature']
domain_set = ["AddToPlaylist", "BookRestaurant", "GetWeather", "PlayMusic", "RateBook", "SearchCreativeWork", "SearchScreeningEvent"]

SLOT_PAD = 0
PAD_INDEX = 0
UNK_INDEX = 1

class Vocab():
    def __init__(self):
        self.word2index = {"PAD":PAD_INDEX, "UNK":UNK_INDEX}
        self.word2count = {}
        self.index2word = {PAD_INDEX: "PAD", UNK_INDEX: "UNK"}
        self.n_words = 2
    def index_words(self, sentence):
        for word in sentence:
            if word not in self.word2index:
                self.word2index[word] = self.n_words
                self.index2word[self.n_words] = word
                self.word2count[word] = 1
                self.n_words+=1
            else:
                self.word2count[word]+=1

def read_file(filepath, vocab, domain=None):
    utter_list, y1_list, y2_list = [], [], []
    with open(filepath, "r") as f:
        for i, line in enumerate(f):
            line = line.strip()  # text \t label
            splits = line.split("\t")
            tokens = splits[0].split()
            l2_list = splits[1].split()

            utter_list.append(tokens)
            y2_list.append(l2_list)

            # update vocab
            vocab.index_words(tokens)

            l1_list = []
            for l in l2_list:
                if "B" in l:
                    l1_list.append("B")
                elif "I" in l:
                    l1_list.append("I")
                else:
                    l1_list.append("O")
            y1_list.append(l1_list)

    data_dict = {"utter": utter_list, "y1": y1_list, "y2": y2_list}
    
    return data_dict, vocab

def binarize_data(data, vocab, dm):
    data_bin = {"utter": [], "y1": [], "y2": [], "domains": []}
    assert len(data_bin["utter"]) == len(data_bin["y1"]) == len(data_bin["y2"])
    dm_idx = domain_set.index(dm)
    for utter_tokens, y1_list, y2_list in zip(data["utter"], data["y1"], data["y2"]):
        utter_bin, y1_bin, y2_bin = [], [], []
        # binarize utterence
        for token in utter_tokens:
            utter_bin.append(vocab.word2index[token])
        data_bin["utter"].append(utter_bin)
        # binarize y1
        for y1 in y1_list:
            y1_bin.append(y1_set.index(y1))
        data_bin["y1"].append(y1_bin)
        # binarize y2
        for y2 in y2_list:
            y2_bin.append(y2_set.index(y2))
        data_bin["y2"].append(y2_bin)
        assert len(utter_bin) == len(y1_bin) == len(y2_bin)
        
        data_bin["domains"].append(dm_idx)
    
    return data_bin

def datareader():
    logger.info("Loading and processing data ...")

    data = {"AddToPlaylist": {}, "BookRestaurant": {}, "GetWeather": {}, "PlayMusic": {}, "RateBook": {}, "SearchCreativeWork": {}, "SearchScreeningEvent": {}}

    # load data and build vocab
    vocab = Vocab()
    AddToPlaylistData, vocab = read_file("data/snips/AddToPlaylist/AddToPlaylist.txt", vocab, domain="AddToPlaylist")
    BookRestaurantData, vocab = read_file("data/snips/BookRestaurant/BookRestaurant.txt", vocab, domain="BookRestaurant")
    GetWeatherData, vocab = read_file("data/snips/GetWeather/GetWeather.txt", vocab, domain="GetWeather")
    PlayMusicData, vocab = read_file("data/snips/PlayMusic/PlayMusic.txt", vocab, domain="PlayMusic")
    RateBookData, vocab = read_file("data/snips/RateBook/RateBook.txt", vocab, domain="RateBook")
    SearchCreativeWorkData, vocab = read_file("data/snips/SearchCreativeWork/SearchCreativeWork.txt", vocab, domain="SearchCreativeWork")
    SearchScreeningEventData, vocab = read_file("data/snips/SearchScreeningEvent/SearchScreeningEvent.txt", vocab, domain="SearchScreeningEvent")

    # binarize data
    data["AddToPlaylist"] = binarize_data(AddToPlaylistData, vocab, "AddToPlaylist")
    data["BookRestaurant"] = binarize_data(BookRestaurantData, vocab, "BookRestaurant")
    data["GetWeather"] = binarize_data(GetWeatherData, vocab, "GetWeather")
    data["PlayMusic"] = binarize_data(PlayMusicData, vocab, "PlayMusic")
    data["RateBook"] = binarize_data(RateBookData, vocab, "RateBook")
    data["SearchCreativeWork"] = binarize_data(SearchCreativeWorkData, vocab, "SearchCreativeWork")
    data["SearchScreeningEvent"] = binarize_data(SearchScreeningEventData, vocab, "SearchScreeningEvent")
    
    return data, vocab
