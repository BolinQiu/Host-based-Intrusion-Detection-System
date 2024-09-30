from platform import node
from tracemalloc import start
from sklearn.feature_extraction import FeatureHasher
from torch_geometric.data import *
from tqdm import tqdm

import re
import numpy as np
import logging
import torch
import os

from config import *
from utils import *



def path2higlist(path):
    '''
        1. 对文件路径而言，我们取目录的子串进行特征编码，比如：
        /home/user/file.txt -> ['/home', '/home/user', '/home/user/file.txt']
        2. 对这些子串分别进行编码[hash(i) for i in substrings]，得到特征向量，作为节点的特征

        该函数为子串提取函数。
        :param path: file path
        :return: substrings
    '''
    substrings = []
    elements = path.strip().split('/')
    for i in elements:
        if len(substrings) != 0:
            substrings.append(substrings[-1] + '/' + i)
        else:
            substrings.append(i)
    return substrings


def ip2higlist(ip):
    '''
        1. 对IP地址而言，我们取IP地址的子串进行特征编码，比如：
        192.168.1.1 -> ['192', '192.168', '192.168.1', '192.168.1.1']
        2. 对这些子串分别进行编码[hash(i) for i in substrings]，得到特征向量，作为节点的特征

        该函数为子串提取函数。
        :param ip: IP address
        :return: substrings
    '''
    substrings = []
    elements = ip.strip().split('.')
    for i in elements:
        if len(substrings) != 0:
            substrings.append(substrings[-1] + '.' + i)
        else:
            substrings.append(i)
    return substrings


def gen_feature():
    '''
        1. 读取node2id.txt文件，获取结点信息和映射关系
        2. 对每个结点，分别取子串进行特征编码，得到特征向量，作为结点的特征
        3. 保存结点特征向量，作为节点的特征

        :return: node2higvec
    '''
    nodeid2msg = gen_nodeid2msg() # 从node2id.txt中获取结点信息和映射关系

    node_msg_dict_list = [] # 保存结点类型和结点信息的字典列表

    for i in tqdm(nodeid2msg.keys(), desc='Loading entities ...'):
        if type(i) == int:
            if 'netflow' in nodeid2msg[i].keys():
                higlist = ['netflow']
                higlist += ip2higlist(nodeid2msg[i]['netflow']) # 取子串
            
            if 'file' in nodeid2msg[i].keys():
                higlist = ['file']
                higlist += path2higlist(nodeid2msg[i]['file']) # 取子串

            if 'subject' in nodeid2msg[i].keys():
                higlist = ['subject']
                higlist += path2higlist(nodeid2msg[i]['subject']) #取子串 
            # print(higlist)
            node_msg_dict_list.append(''.join(higlist))
        
    FH_string = FeatureHasher(n_features=node_embedding_dim, input_type='string') # 特征编码器
    node2higvec = []
    for i in tqdm(node_msg_dict_list, desc='Generating node feature vectors ...'):
        # print(i)
        vec = FH_string.transform([[i]]).toarray() # 编码为特征向量
        node2higvec.append(vec)
    node2higvec = np.array(node2higvec).reshape([-1, node_embedding_dim]) # 转换成numpy数组
    torch.save(node2higvec, node2higvec_path) # 保存特征向量
    return node2higvec


def gen_relation_onehot():
    '''
        1. 对每个边的类型，生成一个one-hot向量，作为边的特征
        2. 保存边的one-hot向量，作为边的特征

        :return: rel2vec
    '''
    relvec = torch.nn.functional.one_hot(torch.arange(0, len(rel2id.keys())//2), num_classes=len(rel2id.keys())//2) # 边的编码为one-hot向量，代表事件属于哪种类型
    rel2vec = {}
    for i in rel2id.keys():
        if type(i) is not int:
            rel2vec[i] = relvec[rel2id[i] - 1]
            rel2vec[relvec[rel2id[i] - 1]] = i
    torch.save(rel2vec, rel2vec_path) # 保存one-hot向量
    return rel2vec


def gen_vectorized_graph(node2higvec, rel2vec):
    '''
        1. 读取events.txt文件，获取事件信息
        2. 遍历每一天的事件，获取该天发生的边信息
        3. 保存边信息，作为时序图的边
        4. 保存时序图数据，作为torch.geometric.data.Data对象

        :return: None
    '''
    events = gen_events() # 从events.txt中获取事件信息

    for day in range(int(start_day), int(end_day)+1): # 遍历每一天的事件
        start_timestamp = datetime_to_ns_time_US(f'2018-0{month}-' + str(day) + ' 00:00:00')
        end_timestamp = datetime_to_ns_time_US(f'2018-0{month}-' + str(day + 1) + ' 00:00:00')

        edge_list = []
        for e in events:
            if start_timestamp < int(e[5]) and int(e[5]) < end_timestamp: # 事件发生在该天
                edge_temp = [int(e[1]), int(e[4]), e[2], e[5]]
                if e[2] in include_edge_type:
                    edge_list.append(edge_temp)# 保存边信息
        print(f'Number of edges for day {day}: {len(edge_list)}')

        if len(edge_list) == 0:
            continue
        dataset = TemporalData() # 实例化一个torch.geometric.data.Data对象，用于保存时序图数据
        src = []
        dst = []
        msg = []
        t = []
        for i in edge_list:
            src.append(i[0])
            dst.append(i[1])
            msg.append(
                torch.cat([torch.from_numpy(node2higvec[i[0]]), rel2vec[i[2]], torch.from_numpy(node2higvec[i[1]])])
            )
            t.append(int(i[3]))
        
        # 保存时序图数据
        dataset.src = torch.tensor(src)
        dataset.dst = torch.tensor(dst)
        dataset.t = torch.tensor(t)
        dataset.msg = torch.tensor(t)
        dataset.msg = torch.vstack(msg)
        dataset.src = dataset.src.to(torch.long)
        dataset.dst = dataset.dst.to(torch.long)
        dataset.msg = dataset.msg.to(torch.float)
        dataset.t = dataset.t.to(torch.long)
        torch.save(dataset, graphs_dir + f"/graph_{month}_" + str(day) + ".TemporalData.simple")# 将时序图数据保存到文件中

if __name__ == '__main__':
    # Step 1: Generate node feature vectors
    node2higvec = gen_feature()
    # Step 2: Generate relation one-hot vectors
    rel2vec = gen_relation_onehot()
    # Step 3: Generate vectorized graph
    gen_vectorized_graph(node2higvec, rel2vec)
    

