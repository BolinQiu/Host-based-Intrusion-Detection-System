# 需要修改load_data()中的文件路径信息
# 主函数中的路径信息也需要根据情况修改

import logging

from utils import *
from config import *
from Model import *

# Setting for logging
logger = logging.getLogger("reconstruction_logger")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(artifact_dir + 'reconstruction.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

@torch.no_grad()
def Reconstruct(inference_data,
          memory,
          gnn,
          link_pred,
          neighbor_loader,
          nodeid2msg,
          path
          ):
    '''
        1. 加载数据
        2. 构建邻居图
        3. 计算节点的embedding
        4. 计算边的embedding
        5. 计算边的loss
        6. 更新记忆和邻居图
        7. 记录每条边的loss
        8. 写入日志
        :param inference_data: 待重构的数据
        :param memory: 记忆网络
        :param gnn: 图神经网络
        :param link_pred: 边预测网络
        :param neighbor_loader: 邻居图加载器
        :param nodeid2msg: 节点ID到消息的映射
        :param path: 时序有向图的路径

        :return: 时间窗口的边损失
    '''
    if os.path.exists(path):
        pass
    else:
        os.mkdir(path)

    memory.eval()# 将模型设置为评估模式
    gnn.eval()
    link_pred.eval()

    memory.reset_state()  # Start with a fresh memory.
    neighbor_loader.reset_state()  # Start with an empty graph.

    time_with_loss = {}  # 格式 key: time，  value： the losses
    total_loss = 0
    edge_list = []

    unique_nodes = torch.tensor([]).to(device=device)
    total_edges = 0


    start_time = inference_data.t[0]
    event_count = 0
    pos_o = []

    # 记录运行时间以评估性能
    start = time.perf_counter()

    for batch in tqdm(inference_data.seq_batches(batch_size=BATCH)): # 遍历每一批数据
        # 加载数据
        src, pos_dst, t, msg = batch.src, batch.dst, batch.t, batch.msg
        unique_nodes = torch.cat([unique_nodes, src, pos_dst]).unique()
        total_edges += BATCH
        # 构建邻居图
        n_id = torch.cat([src, pos_dst]).unique()
        n_id, edge_index, e_id = neighbor_loader(n_id)
        assoc[n_id] = torch.arange(n_id.size(0), device=device)
        # 计算节点的embedding
        z, last_update = memory(n_id)
        z = gnn(z, last_update, edge_index, inference_data.t[e_id], inference_data.msg[e_id])
        # 计算边的embedding
        pos_out = link_pred(z[assoc[src]], z[assoc[pos_dst]])

        pos_o.append(pos_out)
        # 计算边的loss
        y_pred = torch.cat([pos_out], dim=0)
        y_true = []
        for m in msg:
            l = tensor_find(m[node_embedding_dim:-node_embedding_dim], 1) - 1
            y_true.append(l)
        y_true = torch.tensor(y_true).to(device=device)
        y_true = y_true.reshape(-1).to(torch.long).to(device=device)

        loss = criterion(y_pred, y_true)
        total_loss += float(loss) * batch.num_events

        # 更新记忆和邻居图
        memory.update_state(src, pos_dst, t, msg)
        neighbor_loader.insert(src, pos_dst)

        # 计算每条边的loss
        each_edge_loss = cal_pos_edges_loss_multiclass(pos_out, y_true)

        for i in range(len(pos_out)):# 记录每条边的loss
            srcnode = int(src[i])
            dstnode = int(pos_dst[i])
            srcmsg = str(nodeid2msg[srcnode])
            dstmsg = str(nodeid2msg[dstnode])
            t_var = int(t[i])
            edgeindex = tensor_find(msg[i][node_embedding_dim:-node_embedding_dim], 1)
            edge_type = rel2id[edgeindex]
            loss = each_edge_loss[i]

            temp_dic = {}
            temp_dic['loss'] = float(loss)
            temp_dic['srcnode'] = srcnode
            temp_dic['dstnode'] = dstnode
            temp_dic['srcmsg'] = srcmsg
            temp_dic['dstmsg'] = dstmsg
            temp_dic['edge_type'] = edge_type
            temp_dic['time'] = t_var

            edge_list.append(temp_dic)

        event_count += len(batch.src)
        if t[-1] > start_time + time_window_size:
            # 这是一次检查点（一个时间窗口的时间），它记录了当前时间窗口中的所有边损失
            time_interval = ns_time_to_datetime_US(start_time) + "~" + ns_time_to_datetime_US(t[-1])
            end = time.perf_counter()
            time_with_loss[time_interval] = {'loss': loss,

                                             'nodes_count': len(unique_nodes),
                                             'total_edges': total_edges,
                                             'costed_time': (end - start)}

            log = open(path + "/" + time_interval + ".txt", 'w')

            for e in edge_list:
                loss += e['loss']

            loss = loss / event_count # 计算当前时间窗口的平均loss

            # 记录日志
            logger.info(
                f'Time: {time_interval}, Loss: {loss:.4f}, Nodes_count: {len(unique_nodes)}, Edges_count: {event_count}, Cost Time: {(end - start):.2f}s')
            edge_list = sorted(edge_list, key=lambda x: x['loss'], reverse=True)  # 基于边损失对结果进行排序
            for e in edge_list:
                log.write(str(e))# 记录每条边的loss
                log.write("\n")
            event_count = 0
            total_loss = 0
            start_time = t[-1]
            log.close()
            edge_list.clear()

    return time_with_loss

def load_data(days):
    '''
        Load the data for the specified days.
    '''
    data = []
    for day in days:
        data.append(torch.load(graphs_dir + f"graph_{month}_{day}.TemporalData.simple").to(device=device))

    return data


if __name__ == "__main__":
    logger.info("Start logging.")
    days = list(set(IDF_calculate_day + training_day + testing_day)) # 实验涉及到的所有日期
    
    # Step 1: 从node2id.txt文件中加载nodeID和node标签的映射关系
    nodeid2msg = gen_nodeid2msg()

    # Step 2: 加载数据
    print("Loading data...")
    data = load_data(days)

    # Step 3: 加载训练好的模型
    print("Loading trained model...")
    memory, gnn, link_pred, neighbor_loader = torch.load(f"./artifact/models/models.pt",map_location=device)

    # Step 4: 开始产生时间窗口，并同时对边进行重构，记录边的重构误差
    for i in range(len(data)):
        print(f"Reconstructing edges for graph_{month}_{days[i]}...")
        Reconstruct(inference_data=data[i],
             memory=memory,
             gnn=gnn,
             link_pred=link_pred,
             neighbor_loader=neighbor_loader,
             nodeid2msg=nodeid2msg,
             path=artifact_dir + f"graph_{month}_{days[i]}")

