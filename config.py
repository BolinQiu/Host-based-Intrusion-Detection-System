########################################################
#
#                   Artifacts path
#
########################################################

# The directory of the raw logs
from tracemalloc import start


raw_dir = "./Raw_data/"

# The directory to save all artifacts
artifact_dir = "./artifact/"

# The directory to save the vectorized graphs
graphs_dir = artifact_dir + "graphs/"

# The directory to save the models
models_dir = artifact_dir + "models/"

# The directory to save the results after testing
test_re = artifact_dir + "test_re/"

# The directory to save all visualized results
vis_re = artifact_dir + "vis_re/"

# The directory of processed temporal data
tmp_data = artifact_dir + "tmp/"
node2id_path = tmp_data + 'node2id.txt'
event_path = tmp_data + 'event.txt'
node2higvec_path = tmp_data + 'node2higvec'
rel2vec_path = tmp_data + 'rel2vec'


filelist = ['ta1-theia-e3-official-6r.json.9',
 'ta1-theia-e3-official-1r.json.9',
 'ta1-theia-e3-official-6r.json.8',
 'ta1-theia-e3-official-6r.json.12',
 'ta1-theia-e3-official-1r.json.7',
 'ta1-theia-e3-official-6r.json.7',
 'ta1-theia-e3-official-6r.json.5',
 'ta1-theia-e3-official-1r.json.3',
 'ta1-theia-e3-official-6r.json',
 'ta1-theia-e3-official-1r.json.5',
 'ta1-theia-e3-official-6r.json.11',
 'ta1-theia-e3-official-1r.json.4',
 'ta1-theia-e3-official-1r.json.6',
 'ta1-theia-e3-official-5m.json',
 'ta1-theia-e3-official-1r.json.2',
 'ta1-theia-e3-official-6r.json.10',
 'ta1-theia-e3-official-6r.json.4',
 'ta1-theia-e3-official-6r.json.1',
 'ta1-theia-e3-official-3.json',
 'ta1-theia-e3-official-1r.json.8',
 'ta1-theia-e3-official-1r.json.1',
 'ta1-theia-e3-official-6r.json.6',
 'ta1-theia-e3-official-6r.json.2',
 'ta1-theia-e3-official-6r.json.3',
 'ta1-theia-e3-official-1r.json']

########################################################
#
#               Graph semantics
#
########################################################

# The directions of the following edge types need to be reversed
edge_reversed = [
    "EVENT_ACCEPT",
    "EVENT_RECVFROM",
    "EVENT_RECVMSG",
    'EVENT_READ' ,
    'EVENT_READ_SOCKET_PARAMS'
]

# The following edges are the types only considered to construct the
# temporal graph for experiments.
include_edge_type=[
    'EVENT_CONNECT',
    'EVENT_EXECUTE',
    'EVENT_OPEN',
    'EVENT_READ',
    'EVENT_RECVFROM',
    'EVENT_RECVMSG',
    'EVENT_SENDMSG',
    'EVENT_SENDTO',
    'EVENT_WRITE'
]

# The map between edge type and edge ID
rel2id={1: 'EVENT_CONNECT',
 'EVENT_CONNECT': 1,
 2: 'EVENT_EXECUTE',
 'EVENT_EXECUTE': 2,
 3: 'EVENT_OPEN',
 'EVENT_OPEN': 3,
 4: 'EVENT_READ',
 'EVENT_READ': 4,
 5: 'EVENT_RECVFROM',
 'EVENT_RECVFROM': 5,
 6: 'EVENT_RECVMSG',
 'EVENT_RECVMSG': 6,
 7: 'EVENT_SENDMSG',
 'EVENT_SENDMSG': 7,
 8: 'EVENT_SENDTO',
 'EVENT_SENDTO': 8,
 9: 'EVENT_WRITE',
 'EVENT_WRITE': 9}

########################################################
#
#                   Model dimensionality
#
########################################################

# Node Embedding Dimension
node_embedding_dim = 16

# Node State Dimension
node_state_dim = 100

# Neighborhood Sampling Size
neighbor_size = 20

# Edge Embedding Dimension
edge_dim = 100

# The time encoding Dimension
time_dim = 100


########################################################
#
#                   Train&Test
#
########################################################

# Batch size for training and testing
BATCH = 1024

# Parameters for optimizer
lr=0.00005
eps=1e-08
weight_decay=0.01

epoch_num=50

# The size of time window, 60000000000 represent 1 min in nanoseconds.
# The default setting is 15 minutes.
time_window_size = 60000000000 * 15

# Training set and Testing set
month = 4 # 根据数据所在的月份进行调整，对Cadets和Theia数据而言，是在4月份
start_day = 3 # 数据集的起始日期
end_day = 13 # 数据集的终止日期
IDF_calculate_day = [3, 4, 5, 9]
training_day = [3, 4, 5]
testing_day = [10, 11, 12]


########################################################
#
#                   Threshold
#
########################################################

beta_day = 90
