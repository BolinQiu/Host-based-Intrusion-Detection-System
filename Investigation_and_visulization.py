import os

from graphviz import Digraph
import networkx as nx
import datetime
import community.community_louvain as community_louvain
from tqdm import tqdm

from config import *
from utils import *



# 这里需要用户手动填入，Anomaly detection检测出的窗口队列
attack_list = [
    artifact_dir+'/graph_4_10/2018-04-10 13:32:01.621943369~2018-04-10 13:47:36.202106977.txt',
    artifact_dir+'/graph_4_10/2018-04-10 14:04:06.588903734~2018-04-10 14:19:47.001526534.txt',
    artifact_dir+'/graph_4_10/2018-04-10 14:19:47.001526534~2018-04-10 14:35:44.815186327.txt',
    artifact_dir+'/graph_4_10/2018-04-10 14:35:44.815186327~2018-04-10 14:51:19.002026543.txt',

    artifact_dir+'/graph_4_12/2018-04-12 12:29:39.001918544~2018-04-12 12:44:41.501404885.txt',
    artifact_dir+'/graph_4_12/2018-04-12 12:44:41.501404885~2018-04-12 13:01:35.287213632.txt',
    artifact_dir+'/graph_4_12/2018-04-12 13:01:35.287213632~2018-04-12 13:17:33.046840369.txt',
    artifact_dir+'/graph_4_12/2018-04-12 13:17:33.046840369~2018-04-12 13:32:43.346667367.txt'
]


def replace_path_name(path_name):
    # 我们筛选出一些日志中常见的路径，可以合并以简化最后生成的图。不合并的话，生成的图会比较冗杂；合并
    # 并不会改变最终的检测结果。
    replace_dic = {
        '/run/shm/':'/run/shm/*',
        '/home/admin/.cache/mozilla/firefox/':'/home/admin/.cache/mozilla/firefox/*',
        '/home/admin/.mozilla/firefox':'/home/admin/.mozilla/firefox*',
        '/data/replay_logdb/':'/data/replay_logdb/*',
        '/home/admin/.local/share/applications/':'/home/admin/.local/share/applications/*',
        '/usr/share/applications/':'/usr/share/applications/*',
        '/lib/x86_64-linux-gnu/':'/lib/x86_64-linux-gnu/*',
        '/proc/':'/proc/*',
        '/stat':'*/stat',
        '/etc/bash_completion.d/':'/etc/bash_completion.d/*',
        '/usr/bin/python2.7':'/usr/bin/python2.7/*',
        '/usr/lib/python2.7':'/usr/lib/python2.7/*',
        }
    for i in replace_dic:
        if i in path_name:
            return replace_dic[i]
    return path_name




def extract_anomalous_edges(attack_list):
    '''
        1. 从Anomaly detection检测出的窗口队列中提取出异常边。
        2. 预处理异常边，去除无效的边，并将边的属性加入到图中。
        3. 返回预处理完的图。

    :param attack_list: Anomaly detection检测出的窗口队列(list)
    :return: 预处理完的图(networkx.DiGraph)
    '''
    # 从Anomaly detection检测出的窗口队列中提取出异常边，并返回预处理完的图。
    gg = nx.DiGraph()
    count = 0
    for path in tqdm(attack_list):
        if ".txt" in path:
            tempg = nx.DiGraph()
            f = open(path, "r")
            edge_list = []
            for line in f:
                count += 1
                l = line.strip()
                jdata = eval(l)
                edge_list.append(jdata)

            edge_list = sorted(edge_list, key=lambda x: x['loss'], reverse=True)

            loss_list = []
            for i in edge_list:
                loss_list.append(i['loss'])
            loss_mean = mean(loss_list)
            loss_std = std(loss_list)
            print(loss_mean)
            print(loss_std)
            thr = loss_mean + 1.5 * loss_std
            print(thr)
            for e in edge_list:
                if e['loss'] > thr:
                    tempg.add_edge(str(hashgen(replace_path_name(e['srcmsg']))),
                                    str(hashgen(replace_path_name(e['dstmsg']))))
                    gg.add_edge(str(hashgen(replace_path_name(e['srcmsg']))),
                                str(hashgen(replace_path_name(e['dstmsg']))),
                                loss=e['loss'], srcmsg=e['srcmsg'], dstmsg=e['dstmsg'],
                                edge_type=e['edge_type'], timestamp=e['time'])
            f.close()
    return gg


def generate_candidate_subgraphs(gg, partition):
    '''
        1. 利用社区发现算法，将图划分为若干个子图。
        2. 返回子图的集合。

    :param gg: 预处理完的图(networkx.DiGraph)
    :param partition: 社区发现算法的结果(dict)
    :return: 子图的集合(dict)
    '''
    # 利用社区发现算法，将图划分为若干个子图。
    communities = {}
    max_partition = 0
    for i in partition:
        if partition[i] > max_partition:
            max_partition = partition[i]
    for i in range(max_partition + 1):
        communities[i] = nx.DiGraph()
    for e in gg.edges:
        communities[partition[e[0]]].add_edge(e[0], e[1])
        communities[partition[e[1]]].add_edge(e[0], e[1])
    return communities



def attack_edge_flag(msg):
    # 标记攻击边，方便和ground truth对比。
    attack_nodes=[
            '/home/admin/clean',
            '/dev/glx_alsa_675',
            '/home/admin/profile',
            '/tmp/memtrace.so',
            '/var/log/xdev',
             '/var/log/wdev',
            'gtcache',
        '161.116.88.72',
        '146.153.68.151',
        '145.199.103.57',
        '61.130.69.232',
        '5.214.163.155',
        '104.228.117.212',
        '141.43.176.203',
        '7.149.198.40',
        '5.214.163.155',
        '149.52.198.23',
        ]
    flag = False
    for i in attack_nodes:
        if i in msg:
            flag = True
    return flag


def plot_graph(communities):
    '''
        1. 将社区发现算法的结果绘制出来，得到最后的结果。

    :param communities: 子图的集合(dict)
    '''
    # 将社区发现算法的结果绘制出来，得到最后的结果。
    graph_index = 0
    for c in communities:
        dot = Digraph(name="MyPicture", comment="the test", format="pdf")
        dot.graph_attr['rankdir'] = 'LR'

        for e in communities[c].edges:
            try:
                temp_edge = gg.edges[e]
                srcnode = e['srcnode']
                dstnode = e['dstnode']
            except:
                pass

            if True:
                # source node
                if "'subject': '" in temp_edge['srcmsg']:
                    src_shape = 'box'
                elif "'file': '" in temp_edge['srcmsg']:
                    src_shape = 'oval'
                elif "'netflow': '" in temp_edge['srcmsg']:
                    src_shape = 'diamond'
                if attack_edge_flag(temp_edge['srcmsg']):
                    src_node_color = 'red'
                else:
                    src_node_color = 'blue'
                dot.node(name=str(hashgen(replace_path_name(temp_edge['srcmsg']))), label=str(
                    replace_path_name(temp_edge['srcmsg']) + str(
                        partition[str(hashgen(replace_path_name(temp_edge['srcmsg'])))])), color=src_node_color,
                        shape=src_shape)

                # destination node
                if "'subject': '" in temp_edge['dstmsg']:
                    dst_shape = 'box'
                elif "'file': '" in temp_edge['dstmsg']:
                    dst_shape = 'oval'
                elif "'netflow': '" in temp_edge['dstmsg']:
                    dst_shape = 'diamond'
                if attack_edge_flag(temp_edge['dstmsg']):
                    dst_node_color = 'red'
                else:
                    dst_node_color = 'blue'
                dot.node(name=str(hashgen(replace_path_name(temp_edge['dstmsg']))), label=str(
                    replace_path_name(temp_edge['dstmsg']) + str(
                        partition[str(hashgen(replace_path_name(temp_edge['dstmsg'])))])), color=dst_node_color,
                        shape=dst_shape)

                if attack_edge_flag(temp_edge['srcmsg']) and attack_edge_flag(temp_edge['dstmsg']):
                    edge_color = 'red'
                else:
                    edge_color = 'blue'
                dot.edge(str(hashgen(replace_path_name(temp_edge['srcmsg']))),
                        str(hashgen(replace_path_name(temp_edge['dstmsg']))), label=temp_edge['edge_type'],
                        color=edge_color)

        dot.render(f'{artifact_dir}/graph_visual/subgraph_' + str(graph_index), format='pdf', view=False)
        graph_index += 1



if __name__ == '__main__':

    # Step 1: Extract anomalous edges from Anomaly detection result.
    gg = extract_anomalous_edges(attack_list)
    # Step 2: Generate candidate subgraphs using community detection algorithm.
    partition = community_louvain.best_partition(gg.to_undirected())
    # Step 3: Generate final result by generating and plotting subgraphs.
    communities = generate_candidate_subgraphs(gg, partition)
    os.system(f'mkdir -p {artifact_dir}/graph_visual/')
    plot_graph(communities)

