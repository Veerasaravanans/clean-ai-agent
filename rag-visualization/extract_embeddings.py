#!/usr/bin/env python3
"""
extract_embeddings.py - Extract WORD-LEVEL embeddings for 3D semantic visualization

This script creates individual embeddings for each important word from your RAG system,
allowing word-by-word semantic visualization with similarity relationships.
"""

import json
import numpy as np
from pathlib import Path
import sys
import re
from collections import Counter

try:
    import chromadb
    CHROMADB_AVAILABLE = True
except ImportError:
    CHROMADB_AVAILABLE = False
    print("Warning: ChromaDB not available. Install: pip install chromadb")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    print("Warning: sentence-transformers not available. Install: pip install sentence-transformers")

try:
    from sklearn.manifold import TSNE
    TSNE_AVAILABLE = True
except ImportError:
    TSNE_AVAILABLE = False
    print("Warning: sklearn not available for t-SNE. Install: pip install scikit-learn")


class WordLevelEmbeddingExtractor:
    """Extract word-level embeddings for semantic 3D visualization."""
    
    def __init__(self, db_path="./vector_db", prompts_dir="./prompts"):
        self.db_path = Path(db_path)
        self.prompts_dir = Path(prompts_dir)
        self.word_embeddings = {}
        self.word_contexts = {}
        self.model = None
        
    def load_model(self):
        """Load sentence transformer model."""
        if not SENTENCE_TRANSFORMERS_AVAILABLE:
            print("ERROR: sentence-transformers required. Install: pip install sentence-transformers")
            return False
        
        print("Loading embedding model (this may take a minute)...")
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✅ Model loaded")
        return True
    
    def extract_words_from_text(self, text, category):
        """Extract meaningful words from text."""
        # Remove special characters and convert to lowercase
        words = re.findall(r'\b[a-z]{3,}\b', text.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'and', 'for', 'with', 'this', 'that', 'from', 'have', 'has',
            'are', 'was', 'were', 'been', 'will', 'can', 'should', 'would',
            'could', 'may', 'might', 'must', 'shall', 'your', 'you', 'our'
        }
        
        words = [w for w in words if w not in stop_words and len(w) > 2]
        
        # Store context for each word
        for word in words:
            if word not in self.word_contexts:
                self.word_contexts[word] = {
                    'count': 0,
                    'categories': set(),
                    'example_sentences': []
                }
            
            self.word_contexts[word]['count'] += 1
            # IMPORTANT: Store category in lower case for easier matching
            self.word_contexts[word]['categories'].add(category.lower())
            
            # Extract sentence containing this word
            sentences = re.split(r'[.!?]+', text)
            for sentence in sentences:
                if word in sentence.lower() and len(self.word_contexts[word]['example_sentences']) < 3:
                    self.word_contexts[word]['example_sentences'].append(sentence.strip()[:100])
        
        return words
    
    def extract_from_chromadb(self):
        """Extract words from ChromaDB documents."""
        if not CHROMADB_AVAILABLE:
            print("ChromaDB not available. Using fallback method.")
            return False
        
        try:
            print(f"Loading ChromaDB from: {self.db_path}")
            client = chromadb.PersistentClient(path=str(self.db_path))
            collection = client.get_collection(name="prompt_embeddings")
            results = collection.get(include=['metadatas', 'documents'])
            
            print(f"Found {len(results['ids'])} chunks in ChromaDB")
            
            for metadata, document in zip(results['metadatas'], results['documents']):
                category = metadata.get('category', 'unknown')
                if document:
                    self.extract_words_from_text(document, category)
            
            print(f"✅ Extracted {len(self.word_contexts)} unique words")
            return True
            
        except Exception as e:
            print(f"Error extracting from ChromaDB: {e}")
            return False
    
    def extract_from_prompts(self):
        """Extract words from prompt markdown files."""
        print("Extracting words from prompt files...")
        
        prompt_files = list(self.prompts_dir.glob('**/*.md'))
        
        if not prompt_files:
            print(f"No .md files found in {self.prompts_dir}")
            return False
        
        print(f"Found {len(prompt_files)} prompt files")
        
        for file_path in prompt_files:
            category = file_path.stem
            print(f"Processing: {file_path.name}")
            
            try:
                text = file_path.read_text(encoding='utf-8')
                self.extract_words_from_text(text, category)
            except Exception as e:
                print(f"Error reading {file_path}: {e}")
        
        print(f"✅ Extracted {len(self.word_contexts)} unique words")
        return True
    
    def create_word_embeddings(self, max_words=900):
        """Create embeddings for most important words."""
        if not self.model:
            if not self.load_model():
                return False
        
        # Select top words by frequency
        word_freq = {word: ctx['count'] for word, ctx in self.word_contexts.items()}
        top_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:max_words]
        
        print(f"\nCreating embeddings for top {len(top_words)} words...")
        
        words_to_embed = [word for word, _ in top_words]
        embeddings = self.model.encode(words_to_embed, show_progress_bar=True)
        
        for word, embedding in zip(words_to_embed, embeddings):
            self.word_embeddings[word] = embedding.tolist()
        
        print(f"✅ Created {len(self.word_embeddings)} word embeddings")
        return True
    
    def calculate_similarity_matrix(self):
        """Calculate cosine similarity between all word pairs."""
        words = list(self.word_embeddings.keys())
        vectors = np.array([self.word_embeddings[w] for w in words])
        
        # Normalize vectors
        norms = np.linalg.norm(vectors, axis=1, keepdims=True)
        normalized = vectors / norms
        
        # Cosine similarity matrix
        similarity_matrix = np.dot(normalized, normalized.T)
        
        return words, similarity_matrix
    
    def project_to_3d(self, vectors):
        """Project high-dimensional vectors to 3D using t-SNE."""
        if TSNE_AVAILABLE and len(vectors) > 3:
            print("Projecting to 3D using t-SNE...")
            tsne = TSNE(n_components=3, random_state=42, perplexity=min(30, len(vectors)-1))
            positions_3d = tsne.fit_transform(vectors)
            print("✅ t-SNE projection complete")
        else:
            print("Using PCA-like projection...")
            # Simple PCA-like projection
            positions_3d = vectors[:, :3] if vectors.shape[1] >= 3 else np.hstack([vectors, np.zeros((len(vectors), 3-vectors.shape[1]))])
        
        return positions_3d
    
    def export_for_visualization(self, output_file="embedding-data.json"):
        """Export word embeddings in format suitable for 3D visualization."""
        words = list(self.word_embeddings.keys())
        vectors = np.array([self.word_embeddings[w] for w in words])
        
        # Project to 3D
        positions_3d = self.project_to_3d(vectors)
        
        # Calculate similarities
        _, similarity_matrix = self.calculate_similarity_matrix()
        
        # Build export data
        export_data = {
            'words': [],
            'metadata': {
                'total_words': len(words),
                'embedding_dimension': len(self.word_embeddings[words[0]]),
                'model': 'all-MiniLM-L6-v2',
                'projection': 't-SNE' if TSNE_AVAILABLE else 'PCA'
            }
        }
        
        for i, word in enumerate(words):
            ctx = self.word_contexts[word]
            
            # Find top 5 most similar words
            similarities = similarity_matrix[i]
            top_similar_indices = np.argsort(similarities)[-6:-1][::-1]  # Exclude self
            similar_words = [(words[j], float(similarities[j])) for j in top_similar_indices]
            
            export_data['words'].append({
                'word': word,
                'position': {
                    'x': float(positions_3d[i][0]) * 20,  # Scale for better visualization
                    'y': float(positions_3d[i][1]) * 20,
                    'z': float(positions_3d[i][2]) * 20
                },
                'frequency': ctx['count'],
                'categories': list(ctx['categories']),
                'example': ctx['example_sentences'][0] if ctx['example_sentences'] else '',
                'similar_words': similar_words,
                'embedding': self.word_embeddings[word]
            })
        
        # Write to file
        output_path = Path(output_file)
        output_path.write_text(json.dumps(export_data, indent=2))
        print(f"\n✅ Exported {len(words)} words to {output_file}")
        print(f"📊 Categories found: {set(cat for ctx in self.word_contexts.values() for cat in ctx['categories'])}")
        
        return True


def main():
    """Main execution function."""
    print("=" * 60)
    print("🧠 WORD-LEVEL EMBEDDING EXTRACTION FOR 3D VISUALIZATION")
    print("=" * 60)
    
    extractor = WordLevelEmbeddingExtractor()
    
    # Try ChromaDB first
    if extractor.extract_from_chromadb():
        print("\n✅ Extracted words from ChromaDB")
    elif extractor.extract_from_prompts():
        print("\n✅ Extracted words from prompt files")
    else:
        print("\n❌ Could not extract words from any source")
        print("Creating demo data...")
        create_demo_word_data()
        return
    
    # Create embeddings
    if not extractor.create_word_embeddings(max_words=900):
        print("❌ Failed to create embeddings")
        return
    
    # Export for visualization
    extractor.export_for_visualization()
    
    print("\n" + "=" * 60)
    print("✅ COMPLETE! Open embedding-viewer.html in your browser")
    print("=" * 60)


def create_demo_word_data():
    """Create demo word-level data for testing."""
    demo_words = [
        # Media words
        'media', 'play', 'pause', 'next', 'previous', 'radio', 'music', 'audio', 'bluetooth', 'streaming',
        # HVAC words
        'temperature', 'climate', 'heating', 'cooling', 'fan', 'air', 'defrost', 'ventilation', 'auto', 'manual',
        # Navigation words
        'navigation', 'map', 'route', 'destination', 'gps', 'directions', 'traffic', 'location', 'search', 'poi',
        # Control words
        'button', 'press', 'tap', 'swipe', 'screen', 'display', 'touch', 'interface', 'menu', 'settings',
        # Action words
        'increase', 'decrease', 'adjust', 'change', 'set', 'select', 'open', 'close', 'start', 'stop'
    ]
    
    print("Creating demo word embeddings...")
    
    if not SENTENCE_TRANSFORMERS_AVAILABLE:
        print("ERROR: Cannot create demo data without sentence-transformers")
        return
    
    model = SentenceTransformer('all-MiniLM-L6-v2')
    embeddings = model.encode(demo_words)
    
    # Project to 3D
    if TSNE_AVAILABLE:
        tsne = TSNE(n_components=3, random_state=42)
        positions = tsne.fit_transform(embeddings)
    else:
        positions = embeddings[:, :3] * 20
    
    # Calculate similarities
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    normalized = embeddings / norms
    similarity_matrix = np.dot(normalized, normalized.T)
    
    demo_data = {'words': [], 'metadata': {'total_words': len(demo_words)}}
    
    categories = {
        'media': ['media', 'play', 'pause', 'next', 'previous', 'radio', 'music', 'audio', 'bluetooth', 'streaming'],
        'hvac': ['temperature', 'climate', 'heating', 'cooling', 'fan', 'air', 'defrost', 'ventilation', 'auto', 'manual'],
        'navigation': ['navigation', 'map', 'route', 'destination', 'gps', 'directions', 'traffic', 'location', 'search', 'poi'],
        'control': ['button', 'press', 'tap', 'swipe', 'screen', 'display', 'touch', 'interface', 'menu', 'settings'],
        'action': ['increase', 'decrease', 'adjust', 'change', 'set', 'select', 'open', 'close', 'start', 'stop']
    }
    
    for i, word in enumerate(demo_words):
        similarities = similarity_matrix[i]
        top_similar = np.argsort(similarities)[-6:-1][::-1]
        similar_words = [(demo_words[j], float(similarities[j])) for j in top_similar]
        
        word_category = [cat for cat, words in categories.items() if word in words]
        
        demo_data['words'].append({
            'word': word,
            'position': {'x': float(positions[i][0]), 'y': float(positions[i][1]), 'z': float(positions[i][2])},
            'frequency': 10 + i,
            'categories': word_category,
            'example': f'Example sentence with {word}',
            'similar_words': similar_words,
            'embedding': embeddings[i].tolist()
        })
    
    Path('embedding-data.json').write_text(json.dumps(demo_data, indent=2))
    print("✅ Demo data created")


if __name__ == "__main__":
    main()