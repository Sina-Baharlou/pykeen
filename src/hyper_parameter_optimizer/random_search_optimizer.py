# -*- coding: utf-8 -*-add # -*- coding: utf-8 -*-
import random
from collections import OrderedDict

import numpy as np
from sklearn.model_selection import train_test_split

from hyper_parameter_optimizer.abstract_hyper_params_optimizer import AbstractHPOptimizer
from utilities.constants import LEARNING_RATE, MARGIN_LOSS, EMBEDDING_DIM, BATCH_SIZE, NUM_EPOCHS, \
    KG_EMBEDDING_MODEL, NUM_ENTITIES, NUM_RELATIONS, CLASS_NAME, SEED
from utilities.instance_creation_utils import create_mapped_triples, create_negative_triples
from utilities.module_initialization_utils import get_kg_embedding_model
from utilities.train_utils import train


class RandomSearchHPO(AbstractHPOptimizer):

    def __init__(self, evaluator):
        self.evaluator = evaluator

    def optimize_hyperparams(self, config, path_to_kg, device, seed):
        np.random.seed(seed=seed)

        hyperparams_dict = config['hyper_param_optimization']
        learning_rates = hyperparams_dict[LEARNING_RATE]
        margins = hyperparams_dict[MARGIN_LOSS]
        embedding_dims = hyperparams_dict[EMBEDDING_DIM]
        max_iters = hyperparams_dict['max_iters']
        batch_size = hyperparams_dict[BATCH_SIZE]
        num_epochs = hyperparams_dict[NUM_EPOCHS]
        embedding_model = hyperparams_dict[KG_EMBEDDING_MODEL]
        kg_embedding_model_config = OrderedDict()
        kg_embedding_model_config[CLASS_NAME] = embedding_model
        metric_string = self.evaluator.METRIC

        data_params = config['data_params']
        ratio_test_data = data_params['ratio_test_data']

        trained_models = []
        eval_results = []
        train_entity_to_ids = []
        train_rel_to_ids = []
        models_params = []
        pos_triples = np.loadtxt(fname=path_to_kg, dtype=str, comments='@Comment@ Subject Predicate Object')
        neg_triples = create_negative_triples(seed=seed, pos_triples=pos_triples)

        for _ in range(max_iters):
            lr = random.choice(learning_rates)
            margin = random.choice(margins)
            embedding_dim = random.choice(embedding_dims)
            train_pos, test_pos, train_neg, test_neg = train_test_split(pos_triples, neg_triples,
                                                                        test_size=ratio_test_data, random_state=seed)

            mapped_pos_tripels, train_entity_to_id, train_rel_to_id = create_mapped_triples(pos_triples)
            mapped_neg_triples, _, _ = create_mapped_triples(pos_triples, entity_to_id=train_entity_to_id,
                                                             rel_to_id=train_rel_to_id)
            kg_embedding_model_config[NUM_ENTITIES] = len(train_entity_to_id)
            kg_embedding_model_config[NUM_RELATIONS] = len(train_rel_to_id)
            kg_embedding_model_config[EMBEDDING_DIM] = embedding_dim
            kg_embedding_model_config[MARGIN_LOSS] = margin
            kg_embedding_model = get_kg_embedding_model(config=kg_embedding_model_config)
            params = kg_embedding_model_config.copy()
            params[LEARNING_RATE] = lr
            params[NUM_EPOCHS] = num_epochs
            params[SEED] = seed
            models_params.append(params)


            train_entity_to_ids.append(train_entity_to_id)
            train_rel_to_ids.append(train_rel_to_id)

            trained_model = train(kg_embedding_model=kg_embedding_model, learning_rate=lr, num_epochs=num_epochs,
                                  batch_size=batch_size, pos_triples=mapped_pos_tripels, neg_triples=mapped_neg_triples,
                                  device=device, seed=seed)

            # Evaluate trained model
            mapped_pos_test_tripels, _, _ = create_mapped_triples(test_pos)
            eval_result, _ = self.evaluator.start_evaluation(test_data=mapped_pos_test_tripels, kg_embedding_model=trained_model)

            trained_models.append(trained_model)
            eval_results.append(eval_result)

        index_of_max = np.argmax(a=eval_results)

        return trained_models[index_of_max], train_entity_to_ids[index_of_max], train_rel_to_ids[index_of_max], \
               eval_results[index_of_max], metric_string, models_params[index_of_max]
