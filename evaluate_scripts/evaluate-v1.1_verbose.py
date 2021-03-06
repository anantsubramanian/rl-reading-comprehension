""" Official evaluation script for v1.1 of the SQuAD dataset. """
from __future__ import print_function
from collections import Counter
import string
import re
import argparse
import json
import sys

from nltk import word_tokenize, sent_tokenize


def normalize_answer(s):
    """Lower text and remove punctuation, articles and extra whitespace."""
    def remove_articles(text):
        return re.sub(r'\b(a|an|the)\b', ' ', text)

    def white_space_fix(text):
        return ' '.join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return ''.join(ch for ch in text if ch not in exclude)

    def lower(text):
        return text.lower()

    return white_space_fix(remove_articles(remove_punc(lower(s))))


def f1_score(prediction, ground_truth):
    prediction_tokens = normalize_answer(prediction).split()
    ground_truth_tokens = normalize_answer(ground_truth).split()
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0
    precision = 1.0 * num_same / len(prediction_tokens)
    recall = 1.0 * num_same / len(ground_truth_tokens)
    f1 = (2 * precision * recall) / (precision + recall)
    return f1


def exact_match_score(prediction, ground_truth):
    return (normalize_answer(prediction) == normalize_answer(ground_truth))


def metric_max_over_ground_truths(metric_fn, prediction, ground_truths):
    scores_for_ground_truths = []
    for ground_truth in ground_truths:
        score = metric_fn(prediction, ground_truth)
        scores_for_ground_truths.append(score)
    return max(scores_for_ground_truths)


def evaluate(dataset, predictions):
    f1 = exact_match = total = 0
    f1s = {}
    ems = {}
    correct_count = 0.0
    total_count = 0.0
    missed = 0
    zero = 0.0
    for article in dataset:
        for paragraph in article['paragraphs']:
            for qa in paragraph['qas']:
                total += 1
                if qa['id'] not in predictions:
                    message = 'Unanswered question ' + qa['id'] + \
                              ' will receive score 0.'
                    print(message, file=sys.stderr)
                    continue
                ground_truths = list(map(lambda x: x['text'], qa['answers']))
                prediction = predictions[qa['id']]
                f1s[qa['id']] = metric_max_over_ground_truths(f1_score, prediction, ground_truths)
                ems[qa['id']] = metric_max_over_ground_truths(exact_match_score, prediction, ground_truths)
                if f1s[qa['id']] == 0.0:
                  zero += 1
                  sentences = [ x for x in sent_tokenize(paragraph['context']) ]
                  ans_sentence_idxs = []
                  for ans in ground_truths:
                    sentence_list = [ i for i in range(len(sentences)) if ans in sentences[i] ]
                    if len(sentence_list) == 0:
                      ans_sentence_idxs = [ -1 ]
                      missed += 1
                    else:
                      ans_sentence_idxs.append(sentence_list[0])
                  sentences = [ " ".join(word_tokenize(x)) for x in sentences ]
                  prediction_idxs = [ i for i in range(len(sentences)) if prediction in sentences[i] ]
                  if len(prediction_idxs) == 0:
                    prediction_idx = -1
                    missed += 1
                  else:
                    prediction_idx = prediction_idxs[0]
                  if prediction_idx in ans_sentence_idxs:
                    correct_count += 1
                  total_count += 1
                exact_match += metric_max_over_ground_truths(
                    exact_match_score, prediction, ground_truths)
                f1 += metric_max_over_ground_truths(
                    f1_score, prediction, ground_truths)

    exact_match = 100.0 * exact_match / total
    f1 = 100.0 * f1 / total
    correct_sentences = 100.0 * correct_count / total_count
    missed = 100.0 * missed / float(total)
    zero = 100.0 * zero / float(total)

    return {'exact_match': exact_match, 'f1': f1, 'correct_sentences': correct_sentences, 'missed': missed,
            'zero': zero }, f1s, ems


if __name__ == '__main__':
    expected_version = '1.1'
    parser = argparse.ArgumentParser(
        description='Evaluation for SQuAD ' + expected_version)
    parser.add_argument('dataset_file', help='Dataset file')
    parser.add_argument('prediction_file', help='Prediction File')
    args = parser.parse_args()
    with open(args.dataset_file) as dataset_file:
        dataset_json = json.load(dataset_file)
        if (dataset_json['version'] != expected_version):
            print('Evaluation expects v-' + expected_version +
                  ', but got dataset with v-' + dataset_json['version'],
                  file=sys.stderr)
        dataset = dataset_json['data']
    with open(args.prediction_file) as prediction_file:
        predictions = json.load(prediction_file)
    res = evaluate(dataset, predictions)
    print(json.dumps(res[0]))
    json.dump(res[1], open("f1s.json", "w"))
    json.dump(res[2], open("ems.json", "w"))
