import numpy as np
import os
import sys

from collections import defaultdict

DATA_FILE = "../data/data.tsv"


def get_sentences(data=DATA_FILE, tokenize=True):
    #TODO: Morphodita
    SENTENCES = []
    if not os.path.exists(data):
        print("Missing sentence file '{}'".format(data), file=sys.stderr)
    with open(data, "r") as sentence_file:
        for line in sentence_file:
            idx, number, transformation, sentence, tokenized_sentence, r1, r2, r3, r4 = line.strip('\n').split('\t')
            if tokenize:
                SENTENCES.append(tokenized_sentence)
            else:
                SENTENCES.append(sentence)
    return SENTENCES


def _get_comparisons_1(idx, a, b):
    if len(a) == 0:
        return []
    if len(b) == 0:
        return []
    out = []
    r1 = [int(x) for x in a.split(',')]
    r2 = [int(x) for x in b.split(',')]
    for i in r1:
        for j in r2:
            out.append([(idx, i), (i, j)])
            out.append([(idx, j), (i, j)])
    return out


def _get_comparisons_2(idx, a, b):
    if len(a) == 0:
        return []
    if len(b) == 0:
        return []
    out = []
    r1 = [int(x) for x in a.split(",")]
    r2 = [int(x) for x in b.split(",")]
    for i in r1:
        for j in r2:
            out.append([(idx, i), (idx, j)])
    return out


def _get_comparisons_3(idx, paraphrases, other):
    out = []
    for p in paraphrases:
        for o in other:
            out.append([(idx, p), (idx, o)])
    return out


def _get_comparisons(data=DATA_FILE):
    # collecting two types of comparisons:
    # - basic: paraphrase vs. significant change in meaning
    # - advanced: comparisons based on the human judgement
    basic = defaultdict(list)
    advanced = defaultdict(list)

    # first round - collecting indices and seeds
    with open(data, "r") as phil:
        current = 1
        roles = defaultdict(list)
        changes = {}
        for line in phil:
            idx, number, transformation, sentence, r1, r2, r3, r4 = line.strip('\n').split('\t')
            idx, number = int(idx), int(number)
            changes[idx] = transformation
            if number != current:
                seed_idx = int(roles['seed'][0])
                paraphrases = [int(p_idx) for p_idx in roles['paraphrase']]
                for role in roles:
                    if role == 'seed' or role == 'paraphrase':
                        continue
                    basic[role].extend(_get_comparisons_3(seed_idx, paraphrases, roles[role]))
                roles = defaultdict(list)
                current = number

            roles[transformation].append(int(idx))
            comparisons_1 = _get_comparisons_1(idx, r1, r2)
            if transformation == 'seed':
                for c in comparisons_1:
                    advanced[changes[c[0][1]]].append(c)
            else:
                advanced[transformation].extend(comparisons_1)
            comparisons_2 = _get_comparisons_2(idx, r3, r4)
            advanced[transformation].extend(comparisons_2)

        # final
        seed_idx = int(roles['seed'][0])
        paraphrases = [int(p_idx) for p_idx in roles['paraphrase']]
        for role in roles:
            if role == 'seed' or role == 'paraphrase':
                continue
        basic[role].extend(_get_comparisons_3(seed_idx, paraphrases, roles[role]))

    return basic, advanced

def cosine_similarity(a, b):
    # Cosine similarity
    dot = np.dot(a, b)
    norma = np.linalg.norm(a)
    normb = np.linalg.norm(b)
    cos = dot / (norma * normb)
    return cos

def _get_unique_pairs(comparisons1,comparisons2):
    unique_pairs = set()
    for pair in [x for y in comparisons1.values() for x in y]:
        unique_pairs.add(pair[0])
        unique_pairs.add(pair[1])
    for pair in [x for y in comparisons2.values() for x in y]:
        unique_pairs.add(pair[0])
        unique_pairs.add(pair[1])
    return unique_pairs


def _print_results(transformations, transformation_name, comparison_source, CACHE):
    correct, total = 0, 0
    for transformation in transformations:
        for comparison in comparison_source[transformation]:
            total += 1
            if CACHE[comparison[0]] > CACHE[comparison[1]]:
                correct += 1
    print("%s %.3f" % (transformation_name.ljust(20), correct/ total))

def evaluate(embeddings):
    basic, advanced = _get_comparisons()

    #There are repeated couples - caching the already counted distance
    unique_pairs = _get_unique_pairs(basic,advanced)
    CACHE = {x:cosine_similarity(embeddings[x[0]],embeddings[x[1]]) for x in unique_pairs}

    basic_changes = ["different meaning", "nonsense", "minimal change"]
    modality = ["ban","possibility"]
    time = ["past","future"]
    style = ["formal sentence","nonstandard sentence","simple sentence"]
    generalization = ["generalization"]
    opposite_meaning = ["opposite meaning"]

    print("transformation    accuracy")
    print("--------------------------")
    _print_results(basic_changes, "basic", basic, CACHE)
    _print_results(modality, "modality", basic, CACHE)
    _print_results(time, "time", advanced, CACHE)
    _print_results(style, "style", advanced, CACHE)
    _print_results(generalization, "generalization", advanced, CACHE)
    _print_results(opposite_meaning, "opposite meaning", advanced, CACHE)