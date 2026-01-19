"""
rag_tool.py - RAG Tool with ChromaDB

Manages test cases and learned solutions using vector database.
AUTO-INDEXES new Excel files on startup.
"""

import logging
from typing import Optional, List, Dict, Any
from pathlib import Path
from datetime import datetime
import json
import hashlib

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings
    from sentence_transformers import SentenceTransformer
except ImportError:
    chromadb = None
    SentenceTransformer = None

from backend.config import settings

logger = logging.getLogger(__name__)


class RAGTool:
    """RAG tool for test cases and learned solutions management."""
    
    def __init__(self, auto_initialize: bool = True):
        """Initialize RAG tool."""
        self.db_path = Path(settings.vector_db_path)
        self.embedding_model_name = settings.embedding_model
        
        # Collections
        self.test_cases_collection = None
        self.learned_solutions_collection = None
        self.indexed_files_collection = None  # Track indexed files
        
        # ChromaDB client
        self.client = None
        self.embedding_function = None
        
        # Excel parser (lazy load)
        self._parser = None
        
        # Track initialization state
        self._initialized = False
        
        # Test cases directory
        self.test_cases_dir = Path(settings.test_cases_dir)
        
        logger.info("RAG Tool created")
        
        # Auto-initialize if requested
        if auto_initialize:
            try:
                self.initialize()
            except Exception as e:
                logger.warning(f"⚠️ RAG auto-initialization failed: {e}")
                logger.warning("⚠️ RAG will not work until properly initialized")
    
    def initialize(self):
        """
        Initialize ChromaDB and collections.
        Also auto-indexes any new Excel files.
        """
        if self._initialized:
            logger.info("RAG already initialized")
            return True
            
        if chromadb is None:
            logger.error("❌ ChromaDB not installed! Run: pip install chromadb sentence-transformers")
            raise RuntimeError("ChromaDB not available")
        
        logger.info("🔧 Initializing RAG system...")
        
        try:
            # Create DB directory
            self.db_path.mkdir(parents=True, exist_ok=True)
            
            # Initialize ChromaDB client
            self.client = chromadb.PersistentClient(
                path=str(self.db_path),
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=True
                )
            )
            
            # Initialize embedding function
            logger.info(f"📦 Loading embedding model: {self.embedding_model_name}")
            self.embedding_function = SentenceTransformer(self.embedding_model_name)
            
            # Create or get collections
            self.test_cases_collection = self.client.get_or_create_collection(
                name="test_cases",
                metadata={"description": "Test case definitions", "hnsw:space": "cosine"}
            )
            
            self.learned_solutions_collection = self.client.get_or_create_collection(
                name="learned_solutions",
                metadata={"description": "Successful test executions", "hnsw:space": "cosine"}
            )
            
            # Collection to track indexed files
            self.indexed_files_collection = self.client.get_or_create_collection(
                name="indexed_files",
                metadata={"description": "Track indexed Excel files"}
            )
            
            self._initialized = True
            
            logger.info("✅ RAG system initialized")
            logger.info(f"   Test cases: {self.test_cases_collection.count()} items")
            logger.info(f"   Learned solutions: {self.learned_solutions_collection.count()} items")
            
            # AUTO-INDEX: Check and index new Excel files
            self._auto_index_new_files()
            
            return True
            
        except Exception as e:
            logger.error(f"❌ RAG initialization failed: {e}")
            raise
    
    def _get_file_hash(self, file_path: Path) -> str:
        """Calculate MD5 hash of file for change detection."""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    
    def _is_file_indexed(self, file_path: Path) -> bool:
        """Check if file has been indexed (by path and hash)."""
        if not self.indexed_files_collection:
            return False
        
        try:
            file_id = str(file_path.absolute())
            current_hash = self._get_file_hash(file_path)
            
            result = self.indexed_files_collection.get(
                ids=[file_id],
                include=["metadatas"]
            )
            
            if not result["ids"]:
                return False
            
            # Check if hash matches (file hasn't changed)
            stored_hash = result["metadatas"][0].get("file_hash", "")
            if stored_hash != current_hash:
                logger.info(f"📝 File modified: {file_path.name}")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error checking indexed file: {e}")
            return False
    
    def _mark_file_indexed(self, file_path: Path, test_count: int):
        """Mark file as indexed in tracking collection."""
        if not self.indexed_files_collection:
            return
        
        try:
            file_id = str(file_path.absolute())
            file_hash = self._get_file_hash(file_path)
            
            # Create a simple embedding (just needs something for ChromaDB)
            dummy_embedding = self.embedding_function.encode(file_path.name).tolist()
            
            self.indexed_files_collection.upsert(
                ids=[file_id],
                embeddings=[dummy_embedding],
                documents=[file_path.name],
                metadatas=[{
                    "file_name": file_path.name,
                    "file_hash": file_hash,
                    "test_count": test_count,
                    "indexed_at": datetime.now().isoformat()
                }]
            )
            
            logger.info(f"✅ Marked as indexed: {file_path.name} ({test_count} tests)")
            
        except Exception as e:
            logger.error(f"Error marking file indexed: {e}")
    
    def _auto_index_new_files(self):
        """Automatically index any new or modified Excel files."""
        if not self.test_cases_dir.exists():
            logger.warning(f"⚠️ Test cases directory not found: {self.test_cases_dir}")
            return
        
        # Find all Excel files
        excel_files = list(self.test_cases_dir.glob("*.xlsx")) + list(self.test_cases_dir.glob("*.xls"))
        
        if not excel_files:
            logger.info("ℹ️ No Excel files found in test cases directory")
            return
        
        logger.info(f"🔍 Scanning {len(excel_files)} Excel file(s) for new test cases...")
        
        new_files = []
        for file_path in excel_files:
            if not self._is_file_indexed(file_path):
                new_files.append(file_path)
        
        if not new_files:
            logger.info("✅ All Excel files already indexed")
            return
        
        logger.info(f"📥 Found {len(new_files)} new/modified file(s) to index")
        
        # Index each new file
        for file_path in new_files:
            try:
                logger.info(f"📄 Indexing: {file_path.name}")
                result = self.index_test_cases_from_excel(str(file_path), mark_indexed=True)
                logger.info(f"   Added: {result['added']}, Skipped: {result['skipped']}, Errors: {result['errors']}")
            except Exception as e:
                logger.error(f"❌ Failed to index {file_path.name}: {e}")
    
    def refresh_index(self):
        """
        Manually refresh index - re-scan and index new files.
        Call this before test execution to ensure latest files are indexed.
        """
        if not self._initialized:
            logger.warning("⚠️ RAG not initialized")
            return
        
        logger.info("🔄 Refreshing test case index...")
        self._auto_index_new_files()
        logger.info(f"✅ Index refreshed. Total test cases: {self.test_cases_collection.count()}")
    
    # ═══════════════════════════════════════════════════════════════
    # Test Cases Operations
    # ═══════════════════════════════════════════════════════════════
    
    def add_test_case(
        self,
        test_id: str,
        title: str,
        component: str,
        steps: List[str],
        description: Optional[str] = None,
        expected: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Add test case to vector database.
        """
        if not self.test_cases_collection:
            logger.error("❌ RAG not initialized")
            return False
        
        try:
            # Check if already exists
            existing = self.test_cases_collection.get(ids=[test_id])
            if existing["ids"]:
                # Update existing
                pass  # Will be handled by upsert below
            
            # Build document text for embedding
            doc_text = f"{title}. {description or ''} Component: {component}. Steps: {' '.join(steps)}"
            
            # Generate embedding
            embedding = self.embedding_function.encode(doc_text).tolist()
            
            # Prepare metadata
            meta = {
                "test_id": test_id,
                "title": title,
                "component": component,
                "description": description or "",
                "expected": expected or "",
                "step_count": len(steps),
                "created_at": datetime.now().isoformat()
            }
            
            if metadata:
                meta.update(metadata)
            
            # Store in ChromaDB (upsert to handle updates)
            self.test_cases_collection.upsert(
                ids=[test_id],
                embeddings=[embedding],
                documents=[json.dumps({
                    "test_id": test_id,
                    "title": title,
                    "component": component,
                    "steps": steps,
                    "description": description,
                    "expected": expected
                })],
                metadatas=[meta]
            )
            
            logger.debug(f"✅ Added/updated test case: {test_id}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Add test case error: {e}")
            return False
    
    def get_test_description(self, test_id: str) -> Optional[Dict]:
        """
        Retrieve test case by ID.
        """
        if not self.test_cases_collection:
            logger.warning("⚠️ RAG not initialized - returning None")
            return None
        
        try:
            result = self.test_cases_collection.get(
                ids=[test_id],
                include=["documents", "metadatas"]
            )
            
            if not result["ids"]:
                logger.warning(f"⚠️ Test case not found in database: {test_id}")
                logger.info(f"   Available test cases: {self.test_cases_collection.count()}")
                return None
            
            # Parse document
            doc = json.loads(result["documents"][0])
            
            logger.info(f"✅ Retrieved test case: {test_id}")
            logger.info(f"   Title: {doc['title']}")
            logger.info(f"   Steps: {len(doc['steps'])}")
            
            return {
                "test_id": doc["test_id"],
                "title": doc["title"],
                "component": doc["component"],
                "description": doc.get("description", ""),
                "steps": doc["steps"],
                "expected": doc.get("expected", "")
            }
            
        except Exception as e:
            logger.error(f"❌ Get test error: {e}")
            return None
    
    def search_similar_tests(
        self,
        query: str,
        top_k: int = 5,
        min_similarity: Optional[float] = None
    ) -> List[Dict]:
        """Search for similar test cases."""
        if not self.test_cases_collection:
            logger.warning("⚠️ RAG not initialized")
            return []
        
        try:
            query_embedding = self.embedding_function.encode(query).tolist()
            
            results = self.test_cases_collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            if not results["ids"][0]:
                return []
            
            min_sim = min_similarity or settings.rag_min_similarity
            similar_tests = []
            
            for i, test_id in enumerate(results["ids"][0]):
                distance = results["distances"][0][i]
                similarity = 1 - distance
                
                if similarity >= min_sim:
                    doc = json.loads(results["documents"][0][i])
                    doc["similarity"] = similarity
                    similar_tests.append(doc)
            
            logger.info(f"🔍 Found {len(similar_tests)} similar tests")
            return similar_tests
            
        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []
    
    def delete_test_case(self, test_id: str) -> bool:
        """Delete test case from database."""
        if not self.test_cases_collection:
            return False
        
        try:
            self.test_cases_collection.delete(ids=[test_id])
            logger.info(f"🗑️ Deleted test case: {test_id}")
            return True
        except Exception as e:
            logger.error(f"❌ Delete error: {e}")
            return False
    
    def index_test_cases_from_excel(
        self,
        excel_path: str,
        batch_size: int = 50,
        mark_indexed: bool = False
    ) -> Dict[str, int]:
        """
        Index test cases from Excel file.
        """
        if not self.test_cases_collection:
            logger.error("❌ RAG not initialized")
            return {"added": 0, "skipped": 0, "errors": 0}
        
        # Lazy load parser
        if self._parser is None:
            from backend.tools.excel_parser import ExcelParser
            self._parser = ExcelParser()
        
        logger.info(f"📥 Indexing test cases from: {excel_path}")
        
        try:
            # Parse Excel
            test_cases = self._parser.parse_test_cases(excel_path)
            
            if not test_cases:
                logger.warning("⚠️ No test cases found in Excel")
                return {"added": 0, "skipped": 0, "errors": 0}
            
            # Index in batches
            added = 0
            skipped = 0
            errors = 0
            
            for test_case in test_cases:
                try:
                    success = self.add_test_case(
                        test_id=test_case["test_id"],
                        title=test_case["title"],
                        component=test_case["component"],
                        steps=test_case["steps"],
                        description=test_case.get("description", ""),
                        expected=test_case.get("expected", ""),
                        metadata={"type": test_case.get("type", "Test Case")}
                    )
                    
                    if success:
                        added += 1
                    else:
                        skipped += 1
                        
                except Exception as e:
                    logger.error(f"❌ Error indexing {test_case.get('test_id')}: {e}")
                    errors += 1
            
            logger.info(f"✅ Indexing complete: {added} added, {skipped} skipped, {errors} errors")
            
            # Mark file as indexed
            if mark_indexed and added > 0:
                self._mark_file_indexed(Path(excel_path), added)
            
            return {"added": added, "skipped": skipped, "errors": errors}
            
        except Exception as e:
            logger.error(f"❌ Index from Excel error: {e}")
            return {"added": 0, "skipped": 0, "errors": 1}
    
    def index_test_cases_from_directory(
        self,
        directory: str = None,
        pattern: str = "*.xlsx"
    ) -> Dict[str, int]:
        """
        Index test cases from all Excel files in directory.
        """
        if not self.test_cases_collection:
            logger.error("❌ RAG not initialized")
            return {"added": 0, "skipped": 0, "errors": 0, "files": 0}
        
        # Use configured directory if not provided
        if directory is None:
            directory = str(self.test_cases_dir)
        
        # Lazy load parser
        if self._parser is None:
            from backend.tools.excel_parser import ExcelParser
            self._parser = ExcelParser()
        
        logger.info(f"📂 Indexing test cases from directory: {directory}")
        
        try:
            dir_path = Path(directory)
            excel_files = list(dir_path.glob(pattern)) + list(dir_path.glob("*.xls"))
            
            if not excel_files:
                logger.warning("⚠️ No Excel files found")
                return {"added": 0, "skipped": 0, "errors": 0, "files": 0}
            
            total_added = 0
            total_skipped = 0
            total_errors = 0
            files_processed = 0
            
            for file_path in excel_files:
                try:
                    result = self.index_test_cases_from_excel(
                        str(file_path),
                        mark_indexed=True
                    )
                    total_added += result["added"]
                    total_skipped += result["skipped"]
                    total_errors += result["errors"]
                    files_processed += 1
                except Exception as e:
                    logger.error(f"❌ Error processing {file_path.name}: {e}")
                    total_errors += 1
            
            logger.info(f"✅ Indexing complete from {files_processed} files")
            logger.info(f"   {total_added} added, {total_skipped} skipped, {total_errors} errors")
            
            return {
                "added": total_added,
                "skipped": total_skipped,
                "errors": total_errors,
                "files": files_processed
            }
            
        except Exception as e:
            logger.error(f"❌ Index from directory error: {e}")
            return {"added": 0, "skipped": 0, "errors": 1, "files": 0}
    
    # ═══════════════════════════════════════════════════════════════
    # Learned Solutions Operations
    # ═══════════════════════════════════════════════════════════════
    
    def save_learned_solution(
        self,
        test_id: str,
        title: str,
        component: str,
        steps: List[Dict[str, Any]]
    ) -> bool:
        """Save learned solution after successful execution."""
        if not self.learned_solutions_collection:
            logger.warning("⚠️ RAG not initialized")
            return False
        
        try:
            existing = self.get_learned_solution(test_id)
            
            if existing:
                execution_count = existing.get("execution_count", 0) + 1
                success_count = existing.get("success_count", 0) + 1
                success_rate = success_count / execution_count
            else:
                execution_count = 1
                success_count = 1
                success_rate = 1.0
            
            doc_text = f"{title}. Component: {component}. Steps: {len(steps)}"
            embedding = self.embedding_function.encode(doc_text).tolist()
            
            solution_data = {
                "test_id": test_id,
                "title": title,
                "component": component,
                "steps": steps,
                "execution_count": execution_count,
                "success_count": success_count,
                "success_rate": success_rate,
                "last_execution": datetime.now().isoformat(),
                "created_at": existing.get("created_at") if existing else datetime.now().isoformat()
            }
            
            self.learned_solutions_collection.upsert(
                ids=[test_id],
                embeddings=[embedding],
                documents=[json.dumps(solution_data)],
                metadatas=[{
                    "test_id": test_id,
                    "title": title,
                    "component": component,
                    "success_rate": success_rate,
                    "execution_count": execution_count,
                    "last_execution": solution_data["last_execution"]
                }]
            )
            
            logger.info(f"✅ Saved learned solution: {test_id} (success rate: {success_rate:.2%})")
            return True
            
        except Exception as e:
            logger.error(f"❌ Save learned solution error: {e}")
            return False
    
    def get_learned_solution(self, test_id: str) -> Optional[Dict]:
        """Retrieve learned solution by test ID."""
        if not self.learned_solutions_collection:
            logger.info(f"Checking learned solution for: {test_id}")
            logger.info(f"No learned solution found for {test_id}")
            return None
        
        try:
            result = self.learned_solutions_collection.get(
                ids=[test_id],
                include=["documents", "metadatas"]
            )
            
            if not result["ids"]:
                logger.info(f"No learned solution found for {test_id}")
                return None
            
            solution = json.loads(result["documents"][0])
            logger.info(f"✅ Found learned solution: {test_id}")
            
            return solution
            
        except Exception as e:
            logger.error(f"❌ Get learned solution error: {e}")
            return None
    
    def get_all_learned_solutions(self) -> List[str]:
        """Get list of all test IDs with learned solutions."""
        if not self.learned_solutions_collection:
            return []
        
        try:
            results = self.learned_solutions_collection.get()
            return results["ids"]
        except Exception as e:
            logger.error(f"❌ Error getting learned solutions: {e}")
            return []
    
    # ═══════════════════════════════════════════════════════════════
    # Utility Methods
    # ═══════════════════════════════════════════════════════════════
    
    def reset_database(self):
        """Reset all collections (use with caution!)."""
        if not self.client:
            return
        
        try:
            self.client.reset()
            logger.warning("⚠️ Database reset!")
            self._initialized = False
            self.initialize()
        except Exception as e:
            logger.error(f"❌ Reset error: {e}")
    
    def get_stats(self) -> Dict:
        """Get database statistics."""
        if not self.client:
            return {"initialized": False}
        
        return {
            "initialized": True,
            "test_cases_count": self.test_cases_collection.count() if self.test_cases_collection else 0,
            "learned_solutions_count": self.learned_solutions_collection.count() if self.learned_solutions_collection else 0,
            "indexed_files_count": self.indexed_files_collection.count() if self.indexed_files_collection else 0,
            "embedding_model": self.embedding_model_name,
            "db_path": str(self.db_path)
        }