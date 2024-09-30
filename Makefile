prepare:
	mkdir -p ./artifact/

create_database:
	python Data_process.py

embed_graphs:
	python Graph_construction.py

train:
	python Graph_learning.py

Time_windows_construction.py:
	python Time_windows_construction.py

anomalous_queue:
	python Anomalous_queue_construction.py

evaluation:
	python Evaluation.py

attack_visualization:
	python Investigation_and_visualization.py

preprocess: prepare create_database embed_graphs

deep_graph_learning: train

anomaly_detection: Time_windows_construction.py anomalous_queue

pipeline: preprocess deep_graph_learning anomaly_detection evaluation attack_investigation

