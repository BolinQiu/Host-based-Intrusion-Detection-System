import logging
import torch
from utils import *
from config import *


# 开始记录日志
logger = logging.getLogger("anomalous_queue_logger")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(artifact_dir + 'anomalous_queue.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)



def cal_anomaly_loss(loss_list, edge_list):
    '''
        计算并返回可疑成分的数量、平均loss、节点集合、边集合
        :param loss_list: 所有边的loss列表
        :param edge_list: 所有边的列表
        :return: count, loss_avg, node_set, edge_set(可疑边的数量，平均loss，节点集合，边集合)
    '''
    if len(loss_list) != len(edge_list):
        print("error!")
        return 0
    count = 0
    loss_sum = 0
    loss_std = std(loss_list) # 计算loss的标准差
    loss_mean = mean(loss_list) # 计算loss的均值
    edge_set = set()
    node_set = set()

    thr = loss_mean + 1.5 * loss_std # 设定阈值，等于均值加上1.5倍的标准差

    logger.info(f"thr:{thr}")

    for i in range(len(loss_list)):
        if loss_list[i] > thr: # 如果loss大于阈值，则认为是可疑成分
            count += 1
            src_node = edge_list[i][0]
            dst_node = edge_list[i][1]
            loss_sum += loss_list[i]

            node_set.add(src_node)
            node_set.add(dst_node)
            edge_set.add(edge_list[i][0] + edge_list[i][1])
    return count, loss_sum / count, node_set, edge_set


def compute_IDF():
    '''
        计算节点的IDF值
        :return: node_IDF, file_list
    '''

    node_IDF = {}

    file_list = []

    for day in IDF_calculate_day:# 遍历计算IDF的日期
        file_path = artifact_dir + f"graph_{month}_{day}/"
        file_l = os.listdir(file_path)
        for i in file_l:
            file_list.append(file_path + i)

    node_set = {}
    for f_path in tqdm(file_list):
        f = open(f_path)
        for line in f:
            l = line.strip()
            jdata = eval(l)
            if jdata['loss'] > 0:
                if 'netflow' not in str(jdata['srcmsg']):
                    if str(jdata['srcmsg']) not in node_set.keys():
                        node_set[str(jdata['srcmsg'])] = {f_path}
                    else:
                        node_set[str(jdata['srcmsg'])].add(f_path)
                if 'netflow' not in str(jdata['dstmsg']):
                    if str(jdata['dstmsg']) not in node_set.keys():
                        node_set[str(jdata['dstmsg'])] = {f_path}
                    else:
                        node_set[str(jdata['dstmsg'])].add(f_path)
    for n in node_set:
        include_count = len(node_set[n])
        IDF = math.log(len(file_list) / (include_count + 1)) # 计算IDF
        node_IDF[n] = IDF

    torch.save(node_IDF, artifact_dir + "node_IDF") # 保存节点的IDF值
    logger.info("IDF weight calculate complete!")
    return node_IDF, file_list


def is_include_key_word(s):
    # 经过我们的排查，这些结点是系统经常发生的正常行为，在最后肯定不会被作为可疑成分。
    # 因此，此处做个预先排除。可以减少运行时间。当然，不进行这一步也不会影响结果。
    keywords=[
         'netflow',
        'null',
        '/dev/pts',
        'salt-minion.log',
        '675',
        'usr',
         'proc',
        '/.cache/mozilla/',
        'tmp',
        'thunderbird',
        '/bin/',
        '/sbin/sysctl',
        '/data/replay_logdb/',
        '/home/admin/eraseme',
        
        '/stat',
        
      ]
    flag = False
    for i in keywords:
        if i in s:
            flag = True
    return flag


def cal_set_rel(s1, s2, node_IDF, tw_list):
    '''
        计算两个时间窗口之间公共的可疑成分数量
        
        :param s1: 时间窗口1的节点集合
        :param s2: 时间窗口2的节点集合
        :param node_IDF: 节点的IDF值
        :param tw_list: 所有时间窗口的列表
        :return: 公共的可疑成分数量
    '''
    new_s = s1 & s2
    count = 0
    for i in new_s:
        if is_include_key_word(i) is True:
            node_IDF[i] = math.log(len(tw_list) / (1 + len(tw_list))) # 如果结点包含关键词，则给予其较大的IDF值

        if i in node_IDF.keys():
            IDF = node_IDF[i] # 取出结点的IDF值
        else:
            # 对于不在训练集/验证集中，也不在排除列表中的结点，给予其较大的IDF值。
            IDF = math.log(len(tw_list) / (1))

        # 如果IDF值大于90%的最大IDF值，则认为是可疑结点
        if IDF > (math.log(len(tw_list) * 0.9)):
            logger.info(f"node:{i}, IDF:{IDF}")
            count += 1
    return count


def queue_construction(node_IDF, tw_list, graph_dir_path):
    '''
        构建队列
        :param node_IDF: 节点的IDF值
        :param tw_list: 所有时间窗口的列表
        :param graph_dir_path: 图的路径
        :return: 所有窗口队列的列表
    '''
    history_list = []
    current_tw = {}

    file_l = os.listdir(graph_dir_path)
    index_count = 0
    for f_path in sorted(file_l):
        logger.info("**************************************************")
        logger.info(f"Time window: {f_path}")

        f = open(f"{graph_dir_path}/{f_path}")
        edge_loss_list = []
        edge_list = []
        logger.info(f'Time window index: {index_count}')

        # 计算当前时间窗口内的可疑成分
        for line in f:
            l = line.strip()
            jdata = eval(l)
            edge_loss_list.append(jdata['loss'])
            edge_list.append([str(jdata['srcmsg']), str(jdata['dstmsg'])])
        count, loss_avg, node_set, edge_set = cal_anomaly_loss(edge_loss_list, edge_list)
        current_tw['name'] = f_path
        current_tw['loss'] = loss_avg
        current_tw['index'] = index_count
        current_tw['nodeset'] = node_set

        # 递增地构建队列
        added_que_flag = False
        for hq in history_list:
            for his_tw in hq:
                if cal_set_rel(current_tw['nodeset'], his_tw['nodeset'], node_IDF, tw_list) != 0 and current_tw['name'] != his_tw['name']:
                    hq.append(copy.deepcopy(current_tw))
                    added_que_flag = True
                    break
                
        if added_que_flag is False:
            temp_hq = [copy.deepcopy(current_tw)]
            history_list.append(temp_hq)

        index_count += 1


        logger.info(f"Average loss: {loss_avg}")
        logger.info(f"Num of anomalous edges within the time window: {count}")
        logger.info(f"Percentage of anomalous edges: {count / len(edge_list)}")
        logger.info(f"Anomalous node count: {len(node_set)}")
        logger.info(f"Anomalous edge count: {len(edge_set)}")
        logger.info("**************************************************")

    return history_list


if __name__ == '__main__':
    logger.info("Start logging.") # 开始记录日志

    node_IDF, tw_list = compute_IDF() # 计算节点的IDF值


    # 开始构建队列
    for day in testing_day:
        history_list = queue_construction(
            node_IDF=node_IDF,
            tw_list=tw_list,
            graph_dir_path=f"{artifact_dir}/graph_{month}_{day}/"
        )
        torch.save(history_list, f"{artifact_dir}/graph_{month}_{day}_history_list") # 保存队列
