"""
Event Clustering using Semantic Embeddings.
Groups related geopolitical events to identify patterns and connections.
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import logging
import numpy as np
from collections import defaultdict

# Setup logger
try:
    from app.core.logging import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class EventClusterer:
    """
    Clusters related geopolitical events using semantic similarity.
    Identifies event chains, connected incidents, and emerging patterns.
    """
    
    # Clustering configuration
    SIMILARITY_THRESHOLD = 0.65  # Minimum similarity for same cluster
    MIN_CLUSTER_SIZE = 2
    MAX_CLUSTER_SIZE = 50
    
    # Time decay for similarity (events further apart are less related)
    TIME_DECAY_DAYS = 14
    TIME_DECAY_FACTOR = 0.5
    
    def __init__(self, embedding_model: str = "all-MiniLM-L6-v2"):
        """
        Initialize event clusterer.
        
        Args:
            embedding_model: Sentence transformer model for embeddings
        """
        self.embedding_model_name = embedding_model
        self._model = None
        self._initialized = False
        logger.info(f"EventClusterer initialized (model: {embedding_model})")
    
    def _ensure_initialized(self) -> bool:
        """Lazy load embedding model."""
        if self._initialized:
            return self._model is not None
        
        try:
            from sentence_transformers import SentenceTransformer
            
            logger.info(f"Loading embedding model: {self.embedding_model_name}")
            self._model = SentenceTransformer(self.embedding_model_name)
            self._initialized = True
            logger.info("Embedding model loaded successfully")
            return True
            
        except ImportError:
            logger.warning("sentence-transformers not installed")
            self._initialized = True
            return False
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self._initialized = True
            return False
    
    def _get_event_text(self, event: Dict) -> str:
        """Extract text representation from event."""
        parts = []
        
        # Title/headline
        if event.get('title'):
            parts.append(event['title'])
        elif event.get('headline'):
            parts.append(event['headline'])
        
        # Description/content
        if event.get('description'):
            parts.append(event['description'][:500])
        elif event.get('content'):
            parts.append(event['content'][:500])
        elif event.get('notes'):
            parts.append(event['notes'][:500])
        
        # Event type
        if event.get('event_type'):
            parts.append(f"Event type: {event['event_type']}")
        
        # Location
        if event.get('location'):
            parts.append(f"Location: {event['location']}")
        elif event.get('country'):
            parts.append(f"Country: {event['country']}")
        
        # Actors
        if event.get('actor1'):
            parts.append(f"Actor: {event['actor1']}")
        if event.get('actor2'):
            parts.append(f"Target: {event['actor2']}")
        
        return " ".join(parts)
    
    def compute_embeddings(self, events: List[Dict]) -> Optional[np.ndarray]:
        """
        Compute embeddings for events.
        
        Args:
            events: List of event dictionaries
        
        Returns:
            Embedding matrix or None if failed
        """
        if not self._ensure_initialized():
            return None
        
        if not events:
            return None
        
        try:
            texts = [self._get_event_text(e) for e in events]
            embeddings = self._model.encode(texts, show_progress_bar=False)
            return embeddings
        except Exception as e:
            logger.error(f"Error computing embeddings: {e}")
            return None
    
    def compute_similarity_matrix(self, embeddings: np.ndarray, 
                                  events: List[Dict] = None) -> np.ndarray:
        """
        Compute pairwise similarity matrix with optional time decay.
        
        Args:
            embeddings: Event embeddings
            events: Original events (for time decay)
        
        Returns:
            Similarity matrix
        """
        # Cosine similarity
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / norms
        similarity = np.dot(normalized, normalized.T)
        
        # Apply time decay if events provided
        if events:
            for i in range(len(events)):
                for j in range(i + 1, len(events)):
                    time_i = events[i].get('timestamp') or events[i].get('event_date')
                    time_j = events[j].get('timestamp') or events[j].get('event_date')
                    
                    if time_i and time_j:
                        if isinstance(time_i, str):
                            time_i = datetime.fromisoformat(time_i.replace('Z', '+00:00'))
                        if isinstance(time_j, str):
                            time_j = datetime.fromisoformat(time_j.replace('Z', '+00:00'))
                        
                        days_apart = abs((time_i - time_j).days)
                        
                        if days_apart > self.TIME_DECAY_DAYS:
                            decay = self.TIME_DECAY_FACTOR ** (days_apart / self.TIME_DECAY_DAYS)
                            similarity[i, j] *= decay
                            similarity[j, i] *= decay
        
        return similarity
    
    def cluster_hierarchical(self, events: List[Dict], 
                            threshold: float = None) -> List[List[int]]:
        """
        Cluster events using hierarchical agglomerative clustering.
        
        Args:
            events: List of events
            threshold: Similarity threshold
        
        Returns:
            List of clusters (each cluster is list of event indices)
        """
        threshold = threshold or self.SIMILARITY_THRESHOLD
        
        embeddings = self.compute_embeddings(events)
        if embeddings is None:
            return [[i] for i in range(len(events))]  # Each event its own cluster
        
        try:
            from sklearn.cluster import AgglomerativeClustering
            
            # Compute similarity and convert to distance
            similarity = self.compute_similarity_matrix(embeddings, events)
            distance = 1 - similarity
            
            # Hierarchical clustering
            clustering = AgglomerativeClustering(
                n_clusters=None,
                distance_threshold=1 - threshold,
                metric='precomputed',
                linkage='average'
            )
            
            labels = clustering.fit_predict(distance)
            
            # Group by cluster
            clusters = defaultdict(list)
            for i, label in enumerate(labels):
                clusters[label].append(i)
            
            # Filter by size
            valid_clusters = [
                indices for indices in clusters.values()
                if self.MIN_CLUSTER_SIZE <= len(indices) <= self.MAX_CLUSTER_SIZE
            ]
            
            # Add unclustered as singletons
            clustered_indices = set()
            for cluster in valid_clusters:
                clustered_indices.update(cluster)
            
            for i in range(len(events)):
                if i not in clustered_indices:
                    valid_clusters.append([i])
            
            logger.info(f"Formed {len(valid_clusters)} clusters from {len(events)} events")
            return valid_clusters
            
        except Exception as e:
            logger.error(f"Hierarchical clustering failed: {e}")
            return [[i] for i in range(len(events))]
    
    def cluster_dbscan(self, events: List[Dict], 
                      eps: float = 0.35, min_samples: int = 2) -> List[List[int]]:
        """
        Cluster events using DBSCAN (density-based).
        Good for finding clusters of varying density.
        
        Args:
            events: List of events
            eps: Maximum distance between samples
            min_samples: Minimum samples for core point
        
        Returns:
            List of clusters
        """
        embeddings = self.compute_embeddings(events)
        if embeddings is None:
            return [[i] for i in range(len(events))]
        
        try:
            from sklearn.cluster import DBSCAN
            
            clustering = DBSCAN(
                eps=eps,
                min_samples=min_samples,
                metric='cosine'
            )
            
            labels = clustering.fit_predict(embeddings)
            
            # Group by cluster
            clusters = defaultdict(list)
            noise = []
            
            for i, label in enumerate(labels):
                if label == -1:
                    noise.append(i)
                else:
                    clusters[label].append(i)
            
            # Convert to list and add noise as singletons
            result = list(clusters.values())
            result.extend([[i] for i in noise])
            
            logger.info(f"DBSCAN: {len(clusters)} clusters, {len(noise)} noise points")
            return result
            
        except Exception as e:
            logger.error(f"DBSCAN clustering failed: {e}")
            return [[i] for i in range(len(events))]
    
    def find_similar_events(self, query_event: Dict, 
                           events: List[Dict], 
                           top_k: int = 5) -> List[Tuple[int, float]]:
        """
        Find events most similar to query event.
        
        Args:
            query_event: Event to find similar events for
            events: Pool of events to search
            top_k: Number of similar events to return
        
        Returns:
            List of (index, similarity) tuples
        """
        if not self._ensure_initialized():
            return []
        
        if not events:
            return []
        
        try:
            # Get query embedding
            query_text = self._get_event_text(query_event)
            query_embedding = self._model.encode([query_text])[0]
            
            # Get event embeddings
            event_texts = [self._get_event_text(e) for e in events]
            event_embeddings = self._model.encode(event_texts, show_progress_bar=False)
            
            # Compute similarities
            similarities = []
            query_norm = np.linalg.norm(query_embedding)
            
            for i, emb in enumerate(event_embeddings):
                similarity = np.dot(query_embedding, emb) / (query_norm * np.linalg.norm(emb))
                similarities.append((i, float(similarity)))
            
            # Sort by similarity
            similarities.sort(key=lambda x: x[1], reverse=True)
            
            return similarities[:top_k]
            
        except Exception as e:
            logger.error(f"Error finding similar events: {e}")
            return []
    
    def analyze_clusters(self, events: List[Dict], 
                        clusters: List[List[int]]) -> List[Dict]:
        """
        Analyze formed clusters to extract insights.
        
        Args:
            events: Original events
            clusters: Cluster assignments
        
        Returns:
            List of cluster analyses
        """
        analyses = []
        
        for cluster_id, indices in enumerate(clusters):
            if len(indices) < 2:
                continue
            
            cluster_events = [events[i] for i in indices]
            
            # Extract common attributes
            countries = [e.get('country') or e.get('country_code') for e in cluster_events]
            event_types = [e.get('event_type') for e in cluster_events if e.get('event_type')]
            actors = []
            for e in cluster_events:
                if e.get('actor1'):
                    actors.append(e['actor1'])
                if e.get('actor2'):
                    actors.append(e['actor2'])
            
            # Get time range
            timestamps = []
            for e in cluster_events:
                ts = e.get('timestamp') or e.get('event_date')
                if ts:
                    if isinstance(ts, str):
                        ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                    timestamps.append(ts)
            
            # Calculate statistics
            total_fatalities = sum(e.get('fatalities', 0) for e in cluster_events)
            avg_severity = np.mean([e.get('severity', 5) for e in cluster_events])
            
            # Find most common values
            country_counts = defaultdict(int)
            for c in countries:
                if c:
                    country_counts[c] += 1
            
            type_counts = defaultdict(int)
            for t in event_types:
                type_counts[t] += 1
            
            analysis = {
                "cluster_id": cluster_id,
                "event_count": len(indices),
                "event_indices": indices,
                "primary_country": max(country_counts.keys(), key=lambda x: country_counts[x]) if country_counts else None,
                "country_distribution": dict(country_counts),
                "event_types": dict(type_counts),
                "total_fatalities": total_fatalities,
                "average_severity": round(avg_severity, 2),
                "unique_actors": list(set(actors))[:10],
                "time_range": {
                    "start": min(timestamps).isoformat() if timestamps else None,
                    "end": max(timestamps).isoformat() if timestamps else None,
                    "span_days": (max(timestamps) - min(timestamps)).days if len(timestamps) >= 2 else 0
                },
                "cluster_type": self._classify_cluster(cluster_events)
            }
            
            analyses.append(analysis)
        
        return sorted(analyses, key=lambda x: x['event_count'], reverse=True)
    
    def _classify_cluster(self, events: List[Dict]) -> str:
        """Classify cluster type based on event characteristics."""
        if not events:
            return "unknown"
        
        # Check for escalation pattern
        timestamps = []
        severities = []
        for e in events:
            ts = e.get('timestamp') or e.get('event_date')
            if ts:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts.replace('Z', '+00:00'))
                timestamps.append(ts)
                severities.append(e.get('severity', 5))
        
        if len(timestamps) >= 3:
            # Check if severity is increasing with time
            sorted_pairs = sorted(zip(timestamps, severities), key=lambda x: x[0])
            sorted_severities = [s for _, s in sorted_pairs]
            
            if all(sorted_severities[i] <= sorted_severities[i+1] for i in range(len(sorted_severities)-1)):
                return "escalating"
        
        # Check for high intensity
        total_fatalities = sum(e.get('fatalities', 0) for e in events)
        if total_fatalities > 100:
            return "high_intensity"
        
        # Check for recurring
        if len(events) >= 5:
            return "recurring"
        
        # Check event types
        event_types = [e.get('event_type', '') for e in events]
        if any('protest' in t.lower() for t in event_types if t):
            return "civil_unrest"
        if any('attack' in t.lower() or 'battle' in t.lower() for t in event_types if t):
            return "conflict"
        
        return "general"
    
    def detect_event_chains(self, events: List[Dict], 
                           max_days_apart: int = 7) -> List[Dict]:
        """
        Detect chains of related events (causally connected).
        
        Args:
            events: List of events
            max_days_apart: Maximum days between linked events
        
        Returns:
            List of event chains with analysis
        """
        if len(events) < 2:
            return []
        
        # Get embeddings
        embeddings = self.compute_embeddings(events)
        if embeddings is None:
            return []
        
        # Sort events by time
        indexed_events = [(i, e) for i, e in enumerate(events)]
        
        def get_timestamp(e):
            ts = e.get('timestamp') or e.get('event_date')
            if isinstance(ts, str):
                return datetime.fromisoformat(ts.replace('Z', '+00:00'))
            return ts or datetime.min
        
        indexed_events.sort(key=lambda x: get_timestamp(x[1]))
        
        # Find chains
        chains = []
        used_events = set()
        
        for i, (orig_idx, event) in enumerate(indexed_events):
            if orig_idx in used_events:
                continue
            
            chain = [orig_idx]
            chain_events = [event]
            used_events.add(orig_idx)
            
            # Look for subsequent related events
            current_time = get_timestamp(event)
            current_embedding = embeddings[orig_idx]
            
            for j in range(i + 1, len(indexed_events)):
                next_idx, next_event = indexed_events[j]
                
                if next_idx in used_events:
                    continue
                
                next_time = get_timestamp(next_event)
                days_apart = (next_time - current_time).days
                
                if days_apart > max_days_apart:
                    break
                
                # Check similarity
                next_embedding = embeddings[next_idx]
                similarity = np.dot(current_embedding, next_embedding) / (
                    np.linalg.norm(current_embedding) * np.linalg.norm(next_embedding)
                )
                
                if similarity >= self.SIMILARITY_THRESHOLD:
                    chain.append(next_idx)
                    chain_events.append(next_event)
                    used_events.add(next_idx)
                    current_time = next_time
                    current_embedding = next_embedding
            
            if len(chain) >= 2:
                chains.append({
                    "chain_length": len(chain),
                    "event_indices": chain,
                    "start_date": get_timestamp(chain_events[0]).isoformat(),
                    "end_date": get_timestamp(chain_events[-1]).isoformat(),
                    "total_span_days": (get_timestamp(chain_events[-1]) - get_timestamp(chain_events[0])).days,
                    "total_fatalities": sum(e.get('fatalities', 0) for e in chain_events),
                    "countries": list(set(e.get('country') or e.get('country_code') for e in chain_events if e.get('country') or e.get('country_code'))),
                    "is_escalating": self._is_escalating(chain_events)
                })
        
        return sorted(chains, key=lambda x: x['chain_length'], reverse=True)
    
    def _is_escalating(self, events: List[Dict]) -> bool:
        """Check if event chain shows escalation."""
        if len(events) < 2:
            return False
        
        fatalities = [e.get('fatalities', 0) for e in events]
        
        # Check if generally increasing
        increases = sum(1 for i in range(len(fatalities)-1) if fatalities[i+1] > fatalities[i])
        return increases >= len(fatalities) // 2


# Singleton instance
_clusterer = None


def get_event_clusterer() -> EventClusterer:
    """Get or create singleton event clusterer."""
    global _clusterer
    if _clusterer is None:
        _clusterer = EventClusterer()
    return _clusterer


if __name__ == "__main__":
    # Test event clustering
    from datetime import datetime, timedelta
    
    base_date = datetime.utcnow()
    
    test_events = [
        {"title": "Military clash at border post", "country": "IND", "event_type": "Battle", 
         "fatalities": 3, "timestamp": base_date - timedelta(days=7)},
        {"title": "Troops exchange fire at frontier", "country": "IND", "event_type": "Battle",
         "fatalities": 5, "timestamp": base_date - timedelta(days=5)},
        {"title": "Border tensions escalate with shelling", "country": "IND", "event_type": "Shelling",
         "fatalities": 8, "timestamp": base_date - timedelta(days=3)},
        {"title": "Protest erupts in capital", "country": "IND", "event_type": "Protest",
         "fatalities": 0, "timestamp": base_date - timedelta(days=6)},
        {"title": "Demonstrators clash with police", "country": "IND", "event_type": "Riot",
         "fatalities": 2, "timestamp": base_date - timedelta(days=4)},
        {"title": "Economic summit held in city", "country": "IND", "event_type": "Diplomatic",
         "fatalities": 0, "timestamp": base_date - timedelta(days=2)},
        {"title": "Trade agreement signed", "country": "IND", "event_type": "Diplomatic",
         "fatalities": 0, "timestamp": base_date - timedelta(days=1)},
    ]
    
    print("Testing Event Clustering:")
    print("=" * 80)
    
    clusterer = EventClusterer()
    
    # Test hierarchical clustering
    clusters = clusterer.cluster_hierarchical(test_events)
    print(f"\nHierarchical Clustering: {len(clusters)} clusters")
    
    # Analyze clusters
    analyses = clusterer.analyze_clusters(test_events, clusters)
    for analysis in analyses:
        if analysis['event_count'] > 1:
            print(f"\nCluster {analysis['cluster_id']}:")
            print(f"  Events: {analysis['event_count']}")
            print(f"  Type: {analysis['cluster_type']}")
            print(f"  Fatalities: {analysis['total_fatalities']}")
            print(f"  Countries: {analysis['country_distribution']}")
    
    # Test event chains
    print("\n" + "=" * 80)
    print("Event Chains:")
    chains = clusterer.detect_event_chains(test_events)
    for chain in chains:
        print(f"\nChain length: {chain['chain_length']}")
        print(f"  Span: {chain['total_span_days']} days")
        print(f"  Escalating: {chain['is_escalating']}")
        print(f"  Total fatalities: {chain['total_fatalities']}")
