#!/usr/bin/env python3
"""
FAISS Index Manager for Dashboard Context Integration

This manager integrates FAISS-based embedding search with the existing 
dashboard context system to provide efficient similarity-based dashboard selection.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
from datetime import datetime, timedelta

from faiss_embedding_service import FAISSEmbeddingService
from context_manager import DashboardContext, ContextManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('faiss_index_manager.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class FAISSIndexManager:
    """Manages FAISS index integration with dashboard contexts"""
    
    def __init__(self, 
                 context_manager: ContextManager,
                 embedding_service: Optional[FAISSEmbeddingService] = None,
                 index_dir: str = "faiss_index",
                 auto_update: bool = True,
                 update_interval_hours: int = 24):
        """
        Initialize FAISS index manager
        
        Args:
            context_manager: Existing context manager instance
            embedding_service: Optional embedding service instance
            index_dir: Directory for FAISS indexes
            auto_update: Whether to automatically update embeddings
            update_interval_hours: Hours between automatic updates
        """
        self.context_manager = context_manager
        self.embedding_service = embedding_service or FAISSEmbeddingService(index_dir=index_dir)
        self.index_dir = Path(index_dir)
        self.auto_update = auto_update
        self.update_interval = timedelta(hours=update_interval_hours)
        
        # Track last update time
        self.last_update_time = None
        self.index_file = "dashboard_index"
        
        logger.info(f"✅ FAISS Index Manager initialized")
        logger.info(f"   Auto-update: {auto_update}")
        logger.info(f"   Update interval: {update_interval_hours} hours")
    
    def should_update_index(self) -> bool:
        """Check if index should be updated based on time and changes"""
        if not self.auto_update:
            return False
        
        if self.last_update_time is None:
            return True
        
        # Check if enough time has passed
        if datetime.now() - self.last_update_time > self.update_interval:
            return True
        
        # Check if contexts have been updated
        contexts = self.context_manager.get_all_contexts()
        if not contexts:
            return False
        
        # Check if any context has been updated recently
        recent_threshold = datetime.now() - timedelta(hours=1)
        for context in contexts:
            try:
                update_time = datetime.strptime(context.last_update_time, '%Y-%m-%d %H:%M:%S')
                if update_time > recent_threshold:
                    logger.info(f"📅 Found recently updated context: {context.dashboard_name}")
                    return True
            except ValueError:
                continue
        
        return False
    
    def build_index_from_contexts(self, force_rebuild: bool = False) -> bool:
        """
        Build FAISS index from all available dashboard contexts
        
        Args:
            force_rebuild: Whether to force rebuild even if not necessary
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if rebuild is necessary
            if not force_rebuild and not self.should_update_index():
                logger.info("ℹ️ Index rebuild not necessary")
                return False
            
            logger.info("🏗️ Building FAISS index from dashboard contexts...")
            
            # Get all contexts
            contexts = self.context_manager.get_all_contexts()
            if not contexts:
                logger.warning("⚠️ No dashboard contexts found")
                return False
            
            logger.info(f"📋 Found {len(contexts)} dashboard contexts")
            
            # Clear existing index
            self.embedding_service.clear_index()
            
            # Prepare dashboard data for embedding
            dashboard_data = []
            for context in contexts:
                # Convert DashboardContext to dictionary format
                context_dict = {
                    'dashboard_id': context.dashboard_id,
                    'dashboard_name': context.dashboard_name,
                    'dashboard_summary': context.dashboard_summary,
                    'last_update_time': context.last_update_time,
                    'charts': [
                        {
                            'chart_title': chart.chart_title,
                            'chart_summary': chart.chart_summary,
                            'chart_type': chart.chart_type
                        }
                        for chart in context.charts
                    ]
                }
                dashboard_data.append((context.dashboard_id, context_dict))
            
            # Add dashboards to index in batch
            success_count = self.embedding_service.batch_add_dashboards(dashboard_data)
            
            if success_count > 0:
                # Save index to disk
                self.embedding_service.save_index(self.index_file)
                self.last_update_time = datetime.now()
                
                logger.info(f"✅ Successfully built FAISS index with {success_count} dashboards")
                logger.info(f"⏰ Index built at: {self.last_update_time}")
                
                # Log index statistics
                stats = self.embedding_service.get_index_stats()
                logger.info(f"📊 Index stats: {stats}")
                
                return True
            else:
                logger.error("❌ Failed to add any dashboards to index")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to build index from contexts: {e}")
            return False
    
    def load_existing_index(self) -> bool:
        """
        Load existing FAISS index from disk
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Check if index file exists
            index_path = self.index_dir / f"{self.index_file}.faiss"
            if not index_path.exists():
                logger.info(f"ℹ️ No existing index found at {index_path}")
                return False
            
            logger.info(f"📂 Loading existing FAISS index from {index_path}")
            
            success = self.embedding_service.load_index(self.index_file)
            if success:
                self.last_update_time = datetime.now()
                logger.info("✅ Successfully loaded existing FAISS index")
                
                # Log index statistics
                stats = self.embedding_service.get_index_stats()
                logger.info(f"📊 Index stats: {stats}")
                
                return True
            else:
                logger.error("❌ Failed to load existing index")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to load existing index: {e}")
            return False
    
    def search_dashboards(self, query: str, top_k: int = 3) -> List[Tuple[DashboardContext, float]]:
        """
        Search for most relevant dashboards using FAISS similarity search
        
        Args:
            query: Search query text
            top_k: Number of top results to return
            
        Returns:
            List of (DashboardContext, similarity_score) tuples
        """
        try:
            # Ensure index is loaded and up-to-date
            if self.embedding_service.index is None or self.embedding_service.index.ntotal == 0:
                logger.info("🔄 Index not available, attempting to build...")
                if not self.build_index_from_contexts():
                    logger.warning("⚠️ Failed to build index, returning empty results")
                    return []
            
            # Search using FAISS
            results = self.embedding_service.search_similar_dashboards(query, top_k)
            
            if not results:
                logger.warning("⚠️ No search results found")
                return []
            
            # Convert results to DashboardContext objects
            dashboard_results = []
            for dashboard_id, similarity_score, metadata in results:
                # Find the actual DashboardContext object
                contexts = self.context_manager.get_all_contexts()
                for context in contexts:
                    if context.dashboard_id == dashboard_id:
                        dashboard_results.append((context, similarity_score))
                        break
            
            # Sort by similarity score
            dashboard_results.sort(key=lambda x: x[1], reverse=True)
            
            logger.info(f"🔍 Found {len(dashboard_results)} relevant dashboards for query: {query[:50]}...")
            
            # Log top results
            for i, (context, score) in enumerate(dashboard_results[:3]):
                logger.info(f"   {i+1}. {context.dashboard_name} (score: {score:.3f})")
            
            return dashboard_results
            
        except Exception as e:
            logger.error(f"❌ Failed to search dashboards: {e}")
            return []
    
    def add_single_dashboard(self, dashboard_context: DashboardContext) -> bool:
        """
        Add a single dashboard to the FAISS index
        
        Args:
            dashboard_context: DashboardContext object to add
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Convert to dictionary format
            context_dict = {
                'dashboard_id': dashboard_context.dashboard_id,
                'dashboard_name': dashboard_context.dashboard_name,
                'dashboard_summary': dashboard_context.dashboard_summary,
                'last_update_time': dashboard_context.last_update_time,
                'charts': [
                    {
                        'chart_title': chart.chart_title,
                        'chart_summary': chart.chart_summary,
                        'chart_type': chart.chart_type
                    }
                    for chart in dashboard_context.charts
                ]
            }
            
            success = self.embedding_service.add_dashboard_to_index(
                dashboard_context.dashboard_id, context_dict
            )
            
            if success:
                logger.info(f"✅ Added dashboard {dashboard_context.dashboard_name} to index")
                # Save updated index
                self.embedding_service.save_index(self.index_file)
            else:
                logger.error(f"❌ Failed to add dashboard {dashboard_context.dashboard_name} to index")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Failed to add single dashboard: {e}")
            return False
    
    def remove_dashboard(self, dashboard_id: str) -> bool:
        """
        Remove a dashboard from the FAISS index
        
        Args:
            dashboard_id: ID of dashboard to remove
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Note: FAISS doesn't support direct removal, so we need to rebuild
            logger.info(f"🗑️ Removing dashboard {dashboard_id} from index")
            
            # Get all contexts except the one to remove
            contexts = self.context_manager.get_all_contexts()
            filtered_contexts = [ctx for ctx in contexts if ctx.dashboard_id != dashboard_id]
            
            # Rebuild index without the removed dashboard
            self.embedding_service.clear_index()
            
            dashboard_data = []
            for context in filtered_contexts:
                context_dict = {
                    'dashboard_id': context.dashboard_id,
                    'dashboard_name': context.dashboard_name,
                    'dashboard_summary': context.dashboard_summary,
                    'last_update_time': context.last_update_time,
                    'charts': [
                        {
                            'chart_title': chart.chart_title,
                            'chart_summary': chart.chart_summary,
                            'chart_type': chart.chart_type
                        }
                        for chart in context.charts
                    ]
                }
                dashboard_data.append((context.dashboard_id, context_dict))
            
            success_count = self.embedding_service.batch_add_dashboards(dashboard_data)
            
            if success_count >= 0:
                logger.info(f"✅ Successfully removed dashboard {dashboard_id}")
                self.embedding_service.save_index(self.index_file)
                return True
            else:
                logger.error(f"❌ Failed to remove dashboard {dashboard_id}")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to remove dashboard: {e}")
            return False
    
    def get_index_status(self) -> Dict[str, Any]:
        """
        Get current status of the FAISS index
        
        Returns:
            Dictionary with index status information
        """
        stats = self.embedding_service.get_index_stats()
        
        status = {
            'index_loaded': self.embedding_service.index is not None,
            'total_dashboards': stats['total_dashboards'],
            'last_update': self.last_update_time.isoformat() if self.last_update_time else None,
            'auto_update': self.auto_update,
            'update_interval_hours': self.update_interval.total_seconds() / 3600,
            'index_stats': stats,
            'should_update': self.should_update_index()
        }
        
        return status
    
    def force_rebuild(self) -> bool:
        """
        Force rebuild the entire index
        
        Returns:
            True if successful, False otherwise
        """
        logger.info("🔄 Forcing index rebuild...")
        return self.build_index_from_contexts(force_rebuild=True)


# Convenience function for quick initialization
def create_index_manager(context_manager: ContextManager, **kwargs) -> FAISSIndexManager:
    """
    Create and initialize FAISS index manager
    
    Args:
        context_manager: Existing context manager instance
        **kwargs: Additional arguments for FAISSIndexManager
        
    Returns:
        Initialized FAISSIndexManager instance
    """
    return FAISSIndexManager(context_manager, **kwargs)


if __name__ == "__main__":
    # Test the FAISS index manager
    print("🧪 Testing FAISS Index Manager...")
    
    try:
        # Import required modules
        from context_manager import ContextManager
        
        # Initialize context manager
        context_manager = ContextManager()
        print("✅ Context manager initialized")
        
        # Initialize FAISS index manager
        index_manager = create_index_manager(context_manager)
        print("✅ FAISS index manager initialized")
        
        # Try to load existing index
        if index_manager.load_existing_index():
            print("✅ Existing index loaded successfully")
        else:
            print("📝 Building new index...")
            if index_manager.build_index_from_contexts():
                print("✅ New index built successfully")
            else:
                print("❌ Failed to build index")
        
        # Test search
        test_query = "游戏分析"
        print(f"\n🔍 Testing search with query: {test_query}")
        
        results = index_manager.search_dashboards(test_query, top_k=3)
        
        if results:
            print(f"✅ Found {len(results)} results:")
            for i, (context, score) in enumerate(results):
                print(f"   {i+1}. {context.dashboard_name} (score: {score:.3f})")
        else:
            print("❌ No results found")
        
        # Show index status
        status = index_manager.get_index_status()
        print(f"\n📊 Index status: {status}")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()