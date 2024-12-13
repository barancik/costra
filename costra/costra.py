#Costra: A library for evaluating sentence embeddings through comparative analysis.

import os
from collections import defaultdict
from typing import Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd
import pkg_resources


class ComparisonCollector:
    #Handles collection and organization of sentence comparisons.
    
    @staticmethod
    def get_type1_comparisons(idx: int, a: str, b: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        #Collect comparisons testing linear similarity relationships.
        if pd.isna(a) or pd.isna(b):
            return []
            
        comparisons = []
        r1 = [int(x) for x in str(a).split(',') if x and x.strip()]
        r2 = [int(x) for x in str(b).split(',') if x and x.strip()]
        
        for i in r1:
            for j in r2:
                comparisons.extend([
                    ((idx, i), (i, j)),
                    ((idx, j), (i, j))
                ])
        return comparisons

    @staticmethod
    def get_type2_comparisons(idx: int, a: str, b: str) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        #Collect comparisons testing relative similarity relationships.
        if pd.isna(a) or pd.isna(b):
            return []
            
        r1 = [int(x) for x in str(a).split(",") if x and x.strip()]
        r2 = [int(x) for x in str(b).split(",") if x and x.strip()]
        
        return [((idx, i), (idx, j)) for i in r1 for j in r2]

    @staticmethod
    def get_basic_comparisons(idx: int, paraphrases: List[int], others: List[int]) -> List[Tuple[Tuple[int, int], Tuple[int, int]]]:
        #Collect basic paraphrase comparisons.
        return [((idx, p), (idx, o)) for p in paraphrases for o in others]

class CostraEvaluator:
    #Main class for evaluating sentence embeddings using the Costra dataset.
    
    TRANSFORMATION_GROUPS = {
        'basic': ["different meaning", "nonsense", "minimal change"],
        'modality': ["ban", "possibility"],
        'time': ["past", "future"],
        'style': ["formal sentence", "nonstandard sentence", "simple sentence"],
        'generalization': ["generalization"],
        'opposite_meaning': ["opposite meaning"]
    }

    def __init__(self, data_path: Optional[str] = None):
        self.data_path = data_path or pkg_resources.resource_filename("costra", "data/data.tsv")
        self._ensure_data_path_exists()
        self.df = self._load_data()
        
    def _ensure_data_path_exists(self):
        if not os.path.exists(self.data_path):
            raise ValueError(f"Missing input sentence file: '{self.data_path}'")
            
    def _load_data(self) -> pd.DataFrame:
        columns = ['idx', 'number', 'transformation', 'sentence', 'tokenized_sentence', 'r1', 'r2', 'r3', 'r4']
        
        df = pd.read_csv(
            self.data_path, 
            sep='\t', 
            names=columns,
            na_values=[''],  # Treat empty strings as NA
            keep_default_na=True
        )
        
        df['idx'] = df['idx'].astype(int)
        df['number'] = df['number'].astype(int)
        
        for col in ['r1', 'r2', 'r3', 'r4']:
            df[col] = df[col].fillna('')
            
        return df

    def get_sentences(self, tokenize: bool = True) -> List[str]:
        # Extract sentences from the Costra dataset
        return self.df['tokenized_sentence' if tokenize else 'sentence'].tolist()

    def _collect_comparisons(self) -> Tuple[Dict, Dict, int]:
        # Collect all comparison types from the dataset.
        basic = defaultdict(list)
        advanced = defaultdict(list)
        size = len(self.df)

        # Process data group by group
        for number in self.df['number'].unique():
            group = self.df[self.df['number'] == number]
            
            # Get seed and paraphrases
            seed_row = group[group['transformation'] == 'seed'].iloc[0]
            seed_idx = seed_row['idx']
            paraphrases = group[group['transformation'] == 'paraphrase']['idx'].tolist()
            
            # Process each transformation type
            for transformation in group['transformation'].unique():
                if transformation in ('seed', 'paraphrase'):
                    continue
                    
                others = group[group['transformation'] == transformation]['idx'].tolist()
                basic[transformation].extend(
                    ComparisonCollector.get_basic_comparisons(seed_idx, paraphrases, others)
                )
            
            # Process advanced comparisons
            for _, row in group.iterrows():
                type1_comparisons = ComparisonCollector.get_type1_comparisons(
                    row['idx'], row['r1'], row['r2']
                )
                
                if row['transformation'] == 'seed':
                    for c in type1_comparisons:
                        target_transform = self.df.loc[self.df['idx'] == c[0][1], 'transformation'].iloc[0]
                        advanced[target_transform].append(c)
                else:
                    advanced[row['transformation']].extend(type1_comparisons)
                
                type2_comparisons = ComparisonCollector.get_type2_comparisons(
                    row['idx'], row['r3'], row['r4']
                )
                advanced[row['transformation']].extend(type2_comparisons)

        return basic, advanced, size

    @staticmethod
    def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    def evaluate(self, embeddings: np.ndarray) -> Dict[str, float]:
        # Evaluate sentence embeddings using the Costra dataset.
        if not isinstance(embeddings, np.ndarray):
            raise ValueError("Embeddings must be a numpy.ndarray")

        basic, advanced, size = self._collect_comparisons()
        
        if size != embeddings.shape[0]:
            raise ValueError(f"Embedding count ({embeddings.shape[0]}) doesn't match dataset size ({size})")

        # Cache unique comparisons to speed up the process
        unique_pairs = self._get_unique_sentence_pairs(basic, advanced)
        similarity_cache = {
            pair: self.cosine_similarity(embeddings[pair[0]], embeddings[pair[1]])
            for pair in unique_pairs
        }

        results = {}
        for group_name, transformations in self.TRANSFORMATION_GROUPS.items():
            comparison_source = basic if group_name in ('basic', 'modality') else advanced
            correct, total = self._compute_accuracy(
                transformations, comparison_source, similarity_cache)
            results[group_name] = round(correct / total if total > 0 else 0.0, 3)

        # Final score is a simple average of all categories  
        results["costra"] = round(sum(results.values()) / len(results), 3)
        return results

    @staticmethod
    def _get_unique_sentence_pairs(comparisons1: Dict, comparisons2: Dict) -> Set[Tuple[int, int]]:
        unique_pairs = set()
        for pairs in comparisons1.values():
            for pair in pairs:
                unique_pairs.add(pair[0])
                unique_pairs.add(pair[1])
        for pairs in comparisons2.values():
            for pair in pairs:
                unique_pairs.add(pair[0])
                unique_pairs.add(pair[1])
        return unique_pairs

    @staticmethod
    def _compute_accuracy(transformations: List[str], 
                         comparison_source: Dict, 
                         cache: Dict) -> Tuple[int, int]:
        correct = total = 0
        for transformation in transformations:
            for comparison in comparison_source[transformation]:
                total += 1
                if cache[comparison[0]] > cache[comparison[1]]:
                    correct += 1
        return correct, total