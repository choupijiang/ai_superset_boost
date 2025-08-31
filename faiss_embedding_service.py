#!/usr/bin/env python3
"""
FAISS Embedding Service for Dashboard Selection

This service provides efficient embedding-based similarity search using FAISS
and BigModel.cn's text embedding API to replace token-heavy AI selection.
"""

import os
import json
import logging
import pickle
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Try to import required libraries
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("Warning: FAISS not available, please install with: pip install faiss-cpu")

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    NUMPY_AVAILABLE = False
    print("Warning: numpy not available, please install with: pip install numpy")

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    print("Warning: OpenAI not available")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('faiss_embedding_service.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FAISSEmbeddingService:
    """FAISS-based embedding service for dashboard similarity search"""
    
    def __init__(self, 
                 embedding_model: str = "embedding-2",
                 embedding_dimension: int = 1024,
                 index_dir: str = "faiss_index"):
        """
        Initialize FAISS embedding service
        
        Args:
            embedding_model: BigModel.cn embedding model name
            embedding_dimension: Dimension of embedding vectors
            index_dir: Directory to store FAISS indexes
        """
        if not FAISS_AVAILABLE:
            raise ImportError("FAISS is required but not available")
        if not NUMPY_AVAILABLE:
            raise ImportError("numpy is required but not available")
        if not OPENAI_AVAILABLE:
            raise ImportError("OpenAI is required but not available")
        
        self.embedding_model = embedding_model
        self.embedding_dimension = embedding_dimension
        self.index_dir = Path(index_dir)
        self.index_dir.mkdir(exist_ok=True)
        
        # Initialize OpenAI client for BigModel.cn
        self.client = OpenAI(
            api_key=os.environ.get('OPENAI_API_KEY'),
            base_url=os.environ.get('OPENAI_API_BASE')
        )
        
        # Initialize FAISS index
        self.index = None
        self.dashboard_mapping = []  # Maps index positions to dashboard IDs
        self.dashboard_metadata = {}  # Stores dashboard metadata
        
        logger.info(f"✅ FAISS Embedding Service initialized")
        logger.info(f"   Model: {embedding_model}")
        logger.info(f"   Dimension: {embedding_dimension}")
        logger.info(f"   Index directory: {index_dir}")
    
    def create_index(self, index_type: str = "flat") -> None:
        """
        Create FAISS index based on specified type
        
        Args:
            index_type: Type of index ("flat", "ivf", "hnsw")
        """
        if index_type == "flat":
            # Flat index with inner product (cosine similarity)
            self.index = faiss.IndexFlatIP(self.embedding_dimension)
            logger.info("✅ Created FAISS Flat index")
        elif index_type == "ivf":
            # Inverted file index (better for larger datasets)
            nlist = 100  # Number of clusters
            quantizer = faiss.IndexFlatIP(self.embedding_dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dimension, nlist)
            logger.info(f"✅ Created FAISS IVF index with {nlist} clusters")
        elif index_type == "hnsw":
            # Hierarchical navigable small world (fastest search)
            M = 32  # Number of neighbors per node
            ef_construction = 40  # Construction parameter
            self.index = faiss.IndexHNSWFlat(self.embedding_dimension, M)
            self.index.hnsw.efConstruction = ef_construction
            logger.info(f"✅ Created FAISS HNSW index with M={M}, ef_construction={ef_construction}")
        else:
            raise ValueError(f"Unknown index type: {index_type}")
    
    def generate_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Generate embedding for given text using BigModel.cn API
        
        Args:
            text: Input text to embed
            
        Returns:
            Embedding vector as numpy array or None if failed
        """
        try:
            # Clean and prepare text
            text = text.strip()
            if not text:
                logger.warning("⚠️ Empty text provided for embedding")
                return None
            
            # Call BigModel.cn embedding API
            response = self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            # Extract embedding
            embedding = np.array(response.data[0].embedding, dtype=np.float32)
            
            # Normalize for cosine similarity
            embedding = embedding / np.linalg.norm(embedding)
            
            logger.debug(f"✅ Generated embedding with shape: {embedding.shape}")
            return embedding
            
        except Exception as e:
            logger.error(f"❌ Failed to generate embedding: {e}")
            return None
    
    def generate_dashboard_embedding(self, dashboard_context: Dict[str, Any]) -> Optional[np.ndarray]:
        """
        Generate embedding for dashboard context
        
        Args:
            dashboard_context: Dictionary containing dashboard information
            
        Returns:
            Embedding vector or None if failed
        """
        try:
            # Prepare dashboard text for embedding
            text_parts = []
            
            # Add dashboard name
            if 'dashboard_name' in dashboard_context:
                text_parts.append(f"Dashboard Name: {dashboard_context['dashboard_name']}")
            
            # Add dashboard summary
            if 'dashboard_summary' in dashboard_context:
                text_parts.append(f"Summary: {dashboard_context['dashboard_summary']}")
            
            # Add charts information
            if 'charts' in dashboard_context:
                charts_text = []
                for chart in dashboard_context['charts']:
                    if isinstance(chart, dict):
                        chart_title = chart.get('chart_title', '')
                        chart_summary = chart.get('chart_summary', '')
                        if chart_title and chart_summary:
                            charts_text.append(f"{chart_title}: {chart_summary}")
                if charts_text:
                    text_parts.append(f"Charts: {' | '.join(charts_text)}")
            
            # Add metadata
            if 'last_update_time' in dashboard_context:
                text_parts.append(f"Last Updated: {dashboard_context['last_update_time']}")
            
            # Combine all parts
            combined_text = '\n'.join(text_parts)
            
            logger.debug(f"📝 Prepared dashboard text for embedding (length: {len(combined_text)})")
            
            return self.generate_embedding(combined_text)
            
        except Exception as e:
            logger.error(f"❌ Failed to generate dashboard embedding: {e}")
            return None
    
    def add_dashboard_to_index(self, dashboard_id: str, dashboard_context: Dict[str, Any]) -> bool:
        """
        Add dashboard embedding to FAISS index
        
        Args:
            dashboard_id: Unique dashboard identifier
            dashboard_context: Dashboard information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.index is None:
                self.create_index("flat")
            
            # Generate embedding
            embedding = self.generate_dashboard_embedding(dashboard_context)
            if embedding is None:
                return False
            
            # Add to index
            self.index.add(embedding.reshape(1, -1))
            
            # Update mapping and metadata
            self.dashboard_mapping.append(dashboard_id)
            self.dashboard_metadata[dashboard_id] = dashboard_context
            
            logger.info(f"✅ Added dashboard {dashboard_id} to FAISS index")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to add dashboard {dashboard_id} to index: {e}")
            return False
    
    def batch_add_dashboards(self, dashboards: List[Tuple[str, Dict[str, Any]]]) -> int:
        """
        Add multiple dashboards to index in batch
        
        Args:
            dashboards: List of (dashboard_id, dashboard_context) tuples
            
        Returns:
            Number of successfully added dashboards
        """
        if not dashboards:
            return 0
        
        try:
            if self.index is None:
                self.create_index("flat")
            
            # Generate embeddings for all dashboards
            embeddings = []
            valid_ids = []
            valid_contexts = []
            
            for dashboard_id, dashboard_context in dashboards:
                embedding = self.generate_dashboard_embedding(dashboard_context)
                if embedding is not None:
                    embeddings.append(embedding)
                    valid_ids.append(dashboard_id)
                    valid_contexts.append(dashboard_context)
            
            if not embeddings:
                logger.warning("⚠️ No valid embeddings generated for batch")
                return 0
            
            # Convert to numpy array
            embeddings_array = np.array(embeddings, dtype=np.float32)
            
            # Add to index
            self.index.add(embeddings_array)
            
            # Update mapping and metadata
            self.dashboard_mapping.extend(valid_ids)
            for dashboard_id, dashboard_context in zip(valid_ids, valid_contexts):
                self.dashboard_metadata[dashboard_id] = dashboard_context
            
            logger.info(f"✅ Added {len(valid_ids)} dashboards to FAISS index in batch")
            return len(valid_ids)
            
        except Exception as e:
            logger.error(f"❌ Failed to batch add dashboards: {e}")
            return 0
    
    def search_similar_dashboards(self, query: str, top_k: int = 5) -> List[Tuple[str, float, Dict[str, Any]]]:
        """
        Search for most similar dashboards to query
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of (dashboard_id, similarity_score, dashboard_metadata) tuples
        """
        try:
            if self.index is None or self.index.ntotal == 0:
                logger.warning("⚠️ FAISS index is empty")
                return []
            
            # Generate query embedding
            query_embedding = self.generate_embedding(query)
            if query_embedding is None:
                return []
            
            # Search in FAISS index
            scores, indices = self.index.search(query_embedding.reshape(1, -1), top_k)
            
            # Process results
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx >= 0 and idx < len(self.dashboard_mapping):
                    dashboard_id = self.dashboard_mapping[idx]
                    dashboard_metadata = self.dashboard_metadata.get(dashboard_id, {})
                    
                    # Ensure score is in reasonable range
                    similarity_score = max(0.0, min(1.0, float(score)))
                    
                    results.append((dashboard_id, similarity_score, dashboard_metadata))
            
            logger.info(f"🔍 Found {len(results)} similar dashboards for query: {query[:50]}...")
            return results
            
        except Exception as e:
            logger.error(f"❌ Failed to search similar dashboards: {e}")
            return []
    
    def save_index(self, filename: Optional[str] = None) -> bool:
        """
        Save FAISS index and metadata to disk
        
        Args:
            filename: Optional filename, defaults to timestamp
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if self.index is None:
                logger.warning("⚠️ No index to save")
                return False
            
            if filename is None:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"faiss_index_{timestamp}"
            
            # Save FAISS index
            index_path = self.index_dir / f"{filename}.faiss"
            faiss.write_index(self.index, str(index_path))
            
            # Save metadata
            metadata = {
                'dashboard_mapping': self.dashboard_mapping,
                'dashboard_metadata': self.dashboard_metadata,
                'embedding_model': self.embedding_model,
                'embedding_dimension': self.embedding_dimension,
                'created_at': datetime.now().isoformat()
            }
            
            metadata_path = self.index_dir / f"{filename}.pkl"
            with open(metadata_path, 'wb') as f:
                pickle.dump(metadata, f)
            
            logger.info(f"✅ Saved FAISS index to {index_path}")
            logger.info(f"✅ Saved metadata to {metadata_path}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save index: {e}")
            return False
    
    def load_index(self, filename: str) -> bool:
        """
        Load FAISS index and metadata from disk
        
        Args:
            filename: Base filename (without extension)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Load FAISS index
            index_path = self.index_dir / f"{filename}.faiss"
            if not index_path.exists():
                logger.error(f"❌ Index file not found: {index_path}")
                return False
            
            self.index = faiss.read_index(str(index_path))
            
            # Load metadata
            metadata_path = self.index_dir / f"{filename}.pkl"
            if not metadata_path.exists():
                logger.error(f"❌ Metadata file not found: {metadata_path}")
                return False
            
            with open(metadata_path, 'rb') as f:
                metadata = pickle.load(f)
            
            self.dashboard_mapping = metadata['dashboard_mapping']
            self.dashboard_metadata = metadata['dashboard_metadata']
            self.embedding_model = metadata['embedding_model']
            self.embedding_dimension = metadata['embedding_dimension']
            
            logger.info(f"✅ Loaded FAISS index from {index_path}")
            logger.info(f"✅ Loaded {len(self.dashboard_mapping)} dashboards")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load index: {e}")
            return False
    
    def get_index_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the current index
        
        Returns:
            Dictionary with index statistics
        """
        stats = {
            'total_dashboards': len(self.dashboard_mapping),
            'index_type': type(self.index).__name__ if self.index else None,
            'embedding_dimension': self.embedding_dimension,
            'embedding_model': self.embedding_model,
            'index_size': self.index.ntotal if self.index else 0,
            'index_directory': str(self.index_dir)
        }
        
        return stats
    
    def clear_index(self) -> None:
        """Clear current index and metadata"""
        self.index = None
        self.dashboard_mapping = []
        self.dashboard_metadata = {}
        logger.info("🧹 Cleared FAISS index and metadata")


# Convenience function for quick initialization
def create_embedding_service(index_dir: str = "faiss_index") -> FAISSEmbeddingService:
    """
    Create and initialize FAISS embedding service
    
    Args:
        index_dir: Directory for storing indexes
        
    Returns:
        Initialized FAISSEmbeddingService instance
    """
    return FAISSEmbeddingService(index_dir=index_dir)


if __name__ == "__main__":
    # Test the embedding service
    print("🧪 Testing FAISS Embedding Service...")
    
    try:
        service = create_embedding_service()
        print("✅ Service initialized successfully")
        
        # Test embedding generation
        test_text = "这是一个测试文本，用于验证嵌入生成功能。"
        embedding = service.generate_embedding(test_text)
        
        if embedding is not None:
            print(f"✅ Embedding generated successfully: shape {embedding.shape}")
            print(f"✅ Embedding norm: {np.linalg.norm(embedding):.4f}")
        else:
            print("❌ Failed to generate embedding")
        
        # Test index stats
        stats = service.get_index_stats()
        print(f"📊 Index stats: {stats}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()