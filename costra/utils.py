import os

from collections import defaultdict

DATA_FILE = "../data/data.tsv"

def get_sentences(data=DATA_FILE):
    SENTENCES = []
    if not os.path.exists(data):
       print("Missing sentence file '{}'".format(data), file=sys.stderr)
    with open(data,"r") as sentence_file:
        for line in sentence_file:
            idx,number,transformation,sentence,r1,r2,r3,r4 = line.strip('\n').split('\t')
            SENTENCES.append(sentence)
    return SENTENCES

 
def _get_comparisons_1(idx,a,b):
    if len(a) == 0:
        return []
    if len(b) == 0:
        return []
    out = []
    r1 = [int(x) for x in a.split(',')]  
    r2 = [int(x) for x in b.split(',')]
    for i in r1:
        for j in r2:
            out.append([(idx,i),(i,j)])
            out.append([(idx,j),(i,j)])    
    return out


def _get_comparisons_2(idx,a,b):
    if len(a) == 0:
        return []
    if len(b) == 0:
        return []
    out = []
    r1 = [int(x) for x in a.split(",")]
    r2 = [int(x) for x in b.split(",")]
    for i in r1:
        for j in r2:
            out.append([(idx,i),(idx,j)])
    return out


def _get_comparisons_3(idx,paraphrases,other):
    out = []
    for p in paraphrases:
        for o in other:
            out.append([(idx,p),(idx,o)])
    return out


def _get_comparisons(data=DATA_FILE)
    #collecting two types of comparisons:
    # -basic: paraphrase vs. significant change in meaning
    # -advanced: comparisons based on the human judgement
    basic = defaultdict(list)
    advanced = defaultdict(list)

    #prvni kolo - sbiram indexy a seedy   
    with open(DATA_FILE,"r") as phil:
        current = 1
        roles = defaultdict(list)
        changes = {}
        for line in phil:
            idx,number,transformation,sentence,r1,r2,r3,r4 = line.strip('\n').split('\t')
            idx,number = int(idx),int(number)
            changes[idx] = transformation
            if number != current:
                seed_idx = int(roles['seed'][0])
                paraphrases = [int(p_idx) for p_idx in roles['paraphrase']]
                for role in roles:
                    if role == 'seed' or role == 'paraphrase':
                        continue
                    basic[role].extend(_get_comparisons_3(seed_idx,paraphrases,roles[role]))
                roles = defaultdict(list)
                current = number
 
            roles[transformation].append(int(idx))
            comparisons_1 = _get_comparisons_1(idx,r1,r2)
            if transformation == 'seed':
                for c in comparisons_1:
                    advanced[changes[c[0][1]]].append(c)
            else:
                advanced[transformation].extend(comparisons_1)
            comparisons_2 = _get_comparisons_2(idx,r3,r4)
            advanced[transformation].extend(comparisons_2)

        #final
        seed_idx = int(roles['seed'][0])
        paraphrases = [int(p_idx) for p_idx in roles['paraphrase']]
        for role in roles:
            if role == 'seed' or role == 'paraphrase':
                continue
        basic[role].extend(get_comparisons_3(seed_idx,paraphrases,roles[role]))
 
