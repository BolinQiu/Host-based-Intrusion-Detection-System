# 输入：原始数据文件(.json)
# 输出：node2id.txt, event.txt, nodeid2msg.pth
# 修改filelist为需要处理的文件名列表




import cmd
from platform import node
import re
from tqdm import tqdm
import hashlib

from config import *
from utils import *




def stringtomd5(originstr):
    # 字符串转md5
    '''
        1.先将字符串转为byte类型
        2.使用hashlib.sha256()方法对byte类型字符串进行加密
        3.返回加密后的字符串
        :param originstr: origin string
        :return: md5 string
    '''
    originstr = originstr.encode('utf-8')
    signaturemd5 = hashlib.sha256()
    signaturemd5.update(originstr)
    return signaturemd5.hexdigest()


def store_netflow(file_path):
    '''
        将原始数据文件中的NetFlowObject数据提取出来
        :param file_path: file path of raw data
        :return: None
    '''
    netobj2hash = {} # 存储NetFlowObject的hash值和对应的属性信息的映射关系
    for file in tqdm(filelist):# 遍历所有的日志文件
        with open(file_path + file, 'r') as f:
            for line in f: # 对每一条日志用正则表达式进行匹配
                if 'NetFlowObject' in line:
                    try:
                        res = re.findall(
                            'NetFlowObject":{"uuid":"(.*?)"(.*?)"localAddress":"(.*?)","localPort":(.*?),"remoteAddress":"(.*?)","remotePort":(.*?),', 
                            line
                        )[0]

                        nodeid = res[0]
                        srcaddr = res[2]
                        srcport = res[3]
                        dstaddr = res[4]
                        dstport = res[5]

                        nodeproperty = srcaddr + "," + srcport + "," + dstaddr + "," + dstport # 结点信息
                        hashstr = stringtomd5(nodeproperty)
                        netobj2hash[nodeid] = [hashstr, nodeproperty]
                        netobj2hash[hashstr] = nodeid

                    except:
                        pass
    
    datalist = []
    for i in netobj2hash.keys():
        if len(i) != 64:
            # 数据列表的格式 ：[uuid, hashstr(nodeproperty), srcaddr , srcport , dstaddr , dstport]
            datalist.append([i] + [netobj2hash[i][0]] + netobj2hash[i][1].split(","))
    
    return datalist


def store_subject(file_path):
    '''
        将原始数据文件中的SubjectObject数据提取出来
        :param file_path: file path of raw data
        :return: None
    '''
    subject_obj2hash = {} # 存储SubjectObject的hash值和对应的属性信息的映射关系
    for file in tqdm(filelist):
        with open(file_path + file, 'r') as f:
            for line in f: # 对每一条日志用正则表达式进行匹配
                if '{"datum":{"com.bbn.tc.schema.avro.cdm18.Subject"' in line :
                        res=re.findall('Subject":{"uuid":"(.*?)"(.*?)"cmdLine":{"string":"(.*?)"}(.*?)"properties":{"map":{"tgid":"(.*?)"',line)[0]
                        try:
                            path_str=re.findall('"path":"(.*?)"',line)[0] 
                        except:
                            path_str="null"
                        nodeid = res[0]
                        cmdLine = res[2]
                        tgid = res[4]
                        nodeproperty = cmdLine + "," + tgid + "," + path_str # 结点信息
                        hashstr = stringtomd5(nodeproperty)
                        subject_obj2hash[nodeid] = [hashstr, cmdLine, tgid, path_str]
                        subject_obj2hash[hashstr] = nodeid

    datalist = []
    for i in subject_obj2hash.keys():
        if len(i) != 64:
            # 数据列表的格式 ：[uuid, hashstr(exec), exec]
            datalist.append([i] + subject_obj2hash[i])
    print(datalist[-1])
    return datalist


def store_file(file_path):
    '''
        将原始数据文件中的FileObject数据提取出来
        :param file_path: file path of raw data
        :return: None
    '''
    file_obj2hash = {} # 存储FileObject的hash值和对应的属性信息的映射关系

    for file in tqdm(filelist):
        with open(file_path + file, 'r') as f:
            for line in f: # 对每一条日志用正则表达式进行匹配
                if '{"datum":{"com.bbn.tc.schema.avro.cdm18.FileObject"' in line:

                    try:
                        res = re.findall('FileObject":{"uuid":"(.*?)"(.*?)"filename":"(.*?)"', line)[0]
                        nodeid = res[0]
                        filepath = res[2]
                        nodeproperty = filepath # 结点信息
                        hashstr = stringtomd5(nodeproperty)
                        file_obj2hash[nodeid] = [hashstr, filepath]
                        file_obj2hash[hashstr] = nodeid
                    except:
                        pass
        
    datalist = []
    for i in file_obj2hash.keys():
        if len(i) != 64:
            # 数据列表的格式 ：[uuid, hashstr(path_name), path_name]
            datalist.append([i] + file_obj2hash[i])
    print(datalist[-1])

    return datalist


def create_node_list(file_list, subject_list, netflow_list):
    '''
        将三种结点的数据合并，并将结点列表存储在node2id.txt中
        :param file_list: list of file entities
        :param subject_list: list of subject entities
        :param netflow_list: list of netflow entities
        :return: None
    '''
    node_list = {}

    # file
    records = file_list

    for i in records:
        # 格式：hashstr: ["file", path_name]
        node_list[i[1]] = ['file', i[-1]]

    file_uuid2hash = {}
    for i in records:
        # 格式：uuid: hashstr
        file_uuid2hash[i[0]] = i[1]
    
    # subject

    records = subject_list

    for i in records:
        # 格式：hashstr: ["subject", exec]
        node_list[i[1]] = ['subject', i[-1]]
    
    subject_uuid2hash = {}
    for i in records:
        # 格式：uuid: hashstr
        subject_uuid2hash[i[0]] = i[1]

    # netflow

    records = netflow_list
    for i in records:
        # 格式：hashstr: ["netflow", dstaddr:dstport]
        node_list[i[1]] = ["netflow", i[-2] + ":" + i[-1]]
    
    net_uuid2hash = {}
    for i in records:
        # 格式：uuid: hashstr
        net_uuid2hash[i[0]] = i[1]
    

    node_list_database = []
    node_index = 0
    for i in node_list:
        # 结点数据node_list_database的三种格式：
        # hashstr, "file", path_name, node_index
        # hashstr, "subject", exec, node_index
        # hashstr, "netflow", dstaddr:dstport, node_index
        node_list_database.append([i] + node_list[i] + [node_index])
        node_index += 1

    # 将node_list_database存储在node2id.txt中
    with open(node2id_path, 'w') as f:
        for i in tqdm(node_list_database, desc='write node2id.txt'):
            f.write(" ".join([str(j) for j in i]) + "\n")
    
    
    nodeid2msg = {}
    for i in node_list_database:
        nodeid2msg[i[0]] = i[-1] # hashstr: node_index
        nodeid2msg[i[-1]] = {i[1]: i[2]} # node_index: {type: value}
    
    return nodeid2msg, subject_uuid2hash, file_uuid2hash, net_uuid2hash


def store_event(file_path, reverse, nodeid2msg, subject_uuid2hash, file_uuid2hash, net_uuid2hash):
    '''
        将原始数据文件中的Event数据提取出来，并将事件存储在event.txt中
        :param file_path: file path of raw data
        :param reverse: 反转的关系类型列表
        :param nodeid2msg: 结点id和信息的映射关系
        :param subject_uuid2hash: subject uuid和hash的映射关系
        :param file_uuid2hash: file uuid和hash的映射关系
        :param net_uuid2hash: netflow uuid和hash的映射关系
        :return: None
    '''
    datalist = []
    for file in tqdm(filelist):
        with open(file_path + file, 'r') as f:
            for line in f: # 对每一条日志用正则表达式进行匹配，找到每个事件对应的subject和object，并映射成相应的结点信息
                if '{"datum":{"com.bbn.tc.schema.avro.cdm18.Event"' in line and "EVENT_FLOWS_TO" not in line:
                    subject_uuid = re.findall('"subject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}', line)
                    predicateObject_uuid = re.findall('"predicateObject":{"com.bbn.tc.schema.avro.cdm18.UUID":"(.*?)"}', line)
                    if len(subject_uuid) > 0 and len(predicateObject_uuid) > 0:
                        if subject_uuid[0] in subject_uuid2hash and (predicateObject_uuid[0] in file_uuid2hash or predicateObject_uuid[0] in net_uuid2hash):
                            relation_type = re.findall('"type":"(.*?)"', line)[0]
                            time_rec = re.findall('"timestampNanos":(.*?),', line)[0]
                            time_rec = int(time_rec)
                            subjectId = subject_uuid2hash[subject_uuid[0]]
                            if predicateObject_uuid[0] in file_uuid2hash:
                                objectId = file_uuid2hash[predicateObject_uuid[0]]
                            else:
                                objectId = net_uuid2hash[predicateObject_uuid[0]]
                            if relation_type in reverse:
                                # 这些情况需要反转subject和object的关系
                                datalist.append(
                                    [objectId, nodeid2msg[objectId], relation_type, subjectId, nodeid2msg[subjectId], # hash -> index
                                     time_rec])
                            else:
                                datalist.append(
                                    [subjectId, nodeid2msg[subjectId], relation_type, objectId, nodeid2msg[objectId],
                                     time_rec]) # datalist的格式：hash1, index1, re_type, hash2 , index2 ,time_stamp
                                
    # 将datalist存储在event.txt中
    with open(event_path, 'w') as f:
        for i in tqdm(datalist, desc='writing event.txt'):
            f.write(" ".join([str(j) for j in i]) + "\n")



if __name__ == '__main__':

    # Step 1. 分别处理三种结点：netflow. subject, file，并将数据存储在相应的列表中
    print("Processing netflow entities...")
    netflow_list = store_netflow(file_path=raw_dir)

    print("Processing subject entities...")
    subject_list = store_subject(file_path=raw_dir)

    print("Processing file entities...")
    file_list = store_file(file_path=raw_dir)

    # Step 2. 创建结点列表，并将节点列表存储在node2id.txt中
    print("Creating node list...")
    nodeid2msg, subject_uuid2hash, file_uuid2hash, net_uuid2hash = create_node_list(file_list, subject_list, netflow_list)

    # Step 3. 处理事件（也即边），并将事件存储在event.txt中
    print("Processing events...")
    store_event(file_path=raw_dir, 
                reverse=edge_reversed, 
                nodeid2msg=nodeid2msg, 
                subject_uuid2hash=subject_uuid2hash, 
                file_uuid2hash=file_uuid2hash, 
                net_uuid2hash=net_uuid2hash
            )
    
    # min_time, max_time = get_start_end_time()

    # print("Start time:", min_time)
    # print("End time:", max_time)
