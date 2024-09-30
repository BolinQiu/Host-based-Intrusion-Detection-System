# 需要修改，groud_truth_label()函数，填入测试集对应的日期。并根据实际情况，将攻击对应时间段的窗口文件名填入。程序会自动标记好Ground Truth标签。
# 并最后进行效果的评估。
# 需要修改主函数的history_list路径，这个是进行恶意检测的时间段

from sklearn.metrics import confusion_matrix
import logging
from utils import *
from config import *
from Model import *


# Setting for logging
logger = logging.getLogger("evaluation_logger")
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler(artifact_dir + 'evaluation.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


def classifier_evaluation(y_test, y_test_pred):
    '''
        计算分类器的评估指标，包括precision, recall, fscore, accuracy, auc_val
         :param y_test: the ground truth labels
         :param y_test_pred: the predicted labels by the classifier
         :return: precision, recall, fscore, accuracy, auc_val
    '''
    tn, fp, fn, tp =confusion_matrix(y_test, y_test_pred).ravel()
    logger.info(f'tn: {tn}')
    logger.info(f'fp: {fp}')
    logger.info(f'fn: {fn}')
    logger.info(f'tp: {tp}')

    precision=tp/(tp+fp)
    recall=tp/(tp+fn)
    accuracy=(tp+tn)/(tp+tn+fp+fn)
    fscore=2*(precision*recall)/(precision+recall)
    auc_val=roc_auc_score(y_test, y_test_pred)
    logger.info(f"precision: {precision}")
    logger.info(f"recall: {recall}")
    logger.info(f"fscore: {fscore}")
    logger.info(f"accuracy: {accuracy}")
    logger.info(f"auc_val: {auc_val}")
    return precision,recall,fscore,accuracy,auc_val

def ground_truth_label():
    '''
        标记好Ground Truth标签
        :return: labels
    '''
    labels = {}

    for day in testing_day:
        filelist = os.listdir(f"{artifact_dir}/graph_{month}_{day}")
        for f in filelist:
            labels[f] = 0
    # 这里根据Darpa官方给出的ground truth，填入对应的日期和攻击时间段
    attack_list = ['2018-04-10 13:32:01.621943369~2018-04-10 13:47:36.202106977.txt', 
                   '2018-04-10 14:04:06.588903734~2018-04-10 14:19:47.001526534.txt', 
                   '2018-04-10 14:19:47.001526534~2018-04-10 14:35:44.815186327.txt', 
                   '2018-04-10 14:35:44.815186327~2018-04-10 14:51:19.002026543.txt',
                   '2018-04-10 14:51:19.002026543~2018-04-10 15:06:43.093450640.txt',
                   
                   '2018-04-12 12:29:39.001918544~2018-04-12 12:44:41.501404885.txt',
                   '2018-04-12 12:44:41.501404885~2018-04-12 13:01:35.287213632.txt',
                   '2018-04-12 13:01:35.287213632~2018-04-12 13:17:33.046840369.txt',
                   '2018-04-12 13:17:33.046840369~2018-04-12 13:32:43.346667367.txt']
    
    for i in attack_list:
        labels[i] = 1

    return labels


if __name__ == "__main__":
    logger.info("Start logging.")

    # 标记好检测出来的结果
    pred_label = {}

    for day in testing_day:
        filelist = os.listdir(f"{artifact_dir}/graph_{month}_{day}/")
        for f in filelist:
            pred_label[f] = 0


    for day in testing_day:
        history_list = torch.load(f"{artifact_dir}/graph_{month}_{day}_history_list")
        for hl in history_list:
            anomaly_score = 0
            for hq in hl:
                if anomaly_score == 0:
                    anomaly_score = (anomaly_score + 1) * (hq['loss'] + 1)
                else:
                    anomaly_score = (anomaly_score) * (hq['loss'] + 1)
            name_list = []
            if anomaly_score > beta_day:
                name_list = []
                for i in hl:
                    name_list.append(i['name'])
                logger.info(f"Anomalous queue: {name_list}")
                for i in name_list:
                    pred_label[i] = 1
                logger.info(f"Anomaly score: {anomaly_score}")

    # 标记好Ground Truth
    labels = ground_truth_label()
    y = []
    y_pred = []
    for i in labels:
        y.append(labels[i])
        y_pred.append(pred_label[i])
    # 和Ground Truth对比，计算评估指标
    classifier_evaluation(y, y_pred)