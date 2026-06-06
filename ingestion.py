"""
Document Ingestion and Chunking for Knight Circle Reviews

Loads markdown files from data/ folder, cleans them, and chunks them
according to the chunking strategy specified in planning.md:
- Chunk size: 200-600 characters
- Overlap: 0 (no overlap)
- Strategy: Split by paragraph boundaries to preserve semantic meaning
"""

import os
import re
from pathlib import Path
from typing import List, Tuple, Dict, Optional


def extract_metadata_from_header(text: str) -> Dict[str, str]:
    """
    Extract metadata (phase, date, source) from review header.
    
    Format:
    Complex: Knights Circle
    Phase: Phase 1
    Date: June 2022
    Source: r/ucf
    ---
    Review: [actual review text]
    """
    metadata = {
        "complex": "Knights Circle",
        "phase": "Unknown",
        "date": "Unknown",
        "source": "r/ucf"
    }
    
    # Extract phase
    phase_match = re.search(r'Phase:\s*(.+?)(?:\n|$)', text)
    if phase_match:
        metadata["phase"] = phase_match.group(1).strip()
    
    # Extract date
    date_match = re.search(r'Date:\s*(.+?)(?:\n|$)', text)
    if date_match:
        metadata["date"] = date_match.group(1).strip()
    
    # Extract source
    source_match = re.search(r'Source:\s*(.+?)(?:\n|$)', text)
    if source_match:
        metadata["source"] = source_match.group(1).strip()
    
    return metadata


def extract_review_text(text: str) -> str:
    """
    Extract the review text from the document, removing metadata header.
    """
    # Split on the --- separator and take everything after it
    parts = text.split('---')
    if len(parts) >= 2:
        # Take everything after the first separator
        review_section = '---'.join(parts[1:])
        
        # Remove "Review:" label if present
        review_section = re.sub(r'^\s*Review:\s*', '', review_section.strip())
        
        return review_section
    return text


def clean_review_text(text: str) -> str:
    """
    Clean review text of artifacts and unnecessary whitespace.
    """
    # Remove extra newlines but preserve paragraph structure
    text = re.sub(r'\n\n+', '\n\n', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    return text


def split_into_paragraphs(text: str) -> List[str]:
    """
    Split text into paragraphs (separated by blank lines).
    """
    paragraphs = text.split('\n\n')
    return [p.strip() for p in paragraphs if p.strip()]


def create_chunks(paragraphs: List[str], min_size: int = 200, max_size: int = 600) -> List[str]:
    """
    Create chunks of 200-600 characters by combining paragraphs intelligently.
    
    Strategy:
    - Start a new chunk
    - Add paragraphs until we reach min_size (200 chars)
    - Keep adding paragraphs until we'd exceed max_size
    - When we'd exceed, start a new chunk
    """
    chunks = []
    current_chunk = ""
    
    for paragraph in paragraphs:
        # If adding this paragraph would exceed max_size and we already have content
        if current_chunk and len(current_chunk) + len(paragraph) + 2 > max_size:
            # Save current chunk if it's above min_size
            if len(current_chunk) >= min_size:
                chunks.append(current_chunk.strip())
                current_chunk = ""
            else:
                # If current chunk is too small, force-add the paragraph anyway
                current_chunk += "\n\n" + paragraph
                if len(current_chunk) >= min_size:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                continue
        
        # Add paragraph to current chunk
        if current_chunk:
            current_chunk += "\n\n" + paragraph
        else:
            current_chunk = paragraph
    
    # Add final chunk if it has content
    if current_chunk.strip():
        chunks.append(current_chunk.strip())
    
    return chunks


def process_document(file_path: str) -> List[Tuple[str, Dict]]:
    """
    Load a markdown document containing multiple reviews, split them by boundaries,
    extract individual metadata per review, clean, chunk, and return all chunks.
    
    Returns:
        List of (chunk_text, metadata) tuples
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_text = f.read()
    
    # Split the file into individual reviews based on your markdown structure.
    # We use a regex split to catch '---' with optional whitespace/newlines.
    raw_reviews = re.split(r'\n---\n|^-{3,}$,', raw_text)
    
    all_file_chunks = []
    
    for review_entry in raw_reviews:
        review_entry = review_entry.strip()
        if not review_entry:
            continue
            
        # 1. Extract metadata specifically for THIS individual review
        metadata = extract_metadata_from_header(review_entry)
        
        # 2. Strip the metadata header lines out to leave pure review text
        # Removes lines starting with Complex:, Phase:, Date:, Source:
        clean_lines = []
        for line in review_entry.split('\n'):
            if not any(line.strip().startswith(prefix) for prefix in ["Complex:", "Phase:", "Date:", "Source:"]):
                clean_lines.append(line)
        
        pure_review_text = "\n".join(clean_lines).strip()
        
        # 3. Clean and process this specific review's text
        pure_review_text = clean_review_text(pure_review_text)
        paragraphs = split_into_paragraphs(pure_review_text)
        review_chunks = create_chunks(paragraphs, min_size=200, max_size=600)
        
        # 4. Bind the specific metadata to these chunks
        metadata['filename'] = Path(file_path).name
        for chunk in review_chunks:
            all_file_chunks.append((chunk, metadata.copy()))
            
    return all_file_chunks


def load_and_chunk_documents(data_folder: str = "data") -> Tuple[List[str], List[Dict], int]:
    """
    Load all markdown documents from data folder, clean them, and chunk them.
    
    Args:
        data_folder: Path to folder containing markdown files
    
    Returns:
        Tuple of (chunks, metadata_list, total_chunk_count)
        - chunks: List of chunk text strings
        - metadata_list: List of metadata dicts corresponding to each chunk
        - total_chunk_count: Total number of chunks created
    """
    chunks = []
    metadata_list = []
    
    data_path = Path(data_folder)
    
    if not data_path.exists():
        raise FileNotFoundError(f"Data folder '{data_folder}' not found")
    
    # Find all markdown files
    md_files = sorted(data_path.glob("*.md"))
    
    if not md_files:
        raise FileNotFoundError(f"No markdown files found in '{data_folder}'")
    
    print(f"Found {len(md_files)} markdown files to process")
    print("-" * 60)
    
    for file_path in md_files:
        print(f"Processing: {file_path.name}")
        
        try:
            file_chunks = process_document(str(file_path))
            
            # Unzip chunks and metadata
            file_chunk_texts = [chunk for chunk, _ in file_chunks]
            file_metadata = [meta for _, meta in file_chunks]
            
            chunks.extend(file_chunk_texts)
            metadata_list.extend(file_metadata)
            
            print(f"  → Created {len(file_chunk_texts)} chunks")
        except Exception as e:
            print(f"  ⚠ Error processing {file_path.name}: {e}")
    
    total = len(chunks)
    print("-" * 60)
    print(f"Total chunks created: {total}\n")
    
    return chunks, metadata_list, total


def inspect_chunks(chunks: List[str], metadata_list: List[Dict], num_to_show: int = 5):
    """
    Display sample chunks and inspect them for quality.
    """
    print("=" * 80)
    print("CHUNK INSPECTION (5 representative chunks)")
    print("=" * 80)
    
    # Show evenly distributed chunks
    indices = [int(i * len(chunks) / num_to_show) for i in range(num_to_show)]
    
    for idx, chunk_idx in enumerate(indices, 1):
        chunk = chunks[chunk_idx]
        meta = metadata_list[chunk_idx]
        
        print(f"\n[CHUNK {idx}]")
        print(f"File: {meta['filename']} | Phase: {meta['phase']} | Date: {meta['date']}")
        print(f"Size: {len(chunk)} chars | Words: {len(chunk.split())}")
        print("-" * 80)
        print(chunk[:500] + ("..." if len(chunk) > 500 else ""))
        print("-" * 80)
        
        # Basic quality checks
        checks = {
            "✓ Within size range (200-600)": 200 <= len(chunk) <= 600,
            "✓ No HTML artifacts": "&" not in chunk or "&" in chunk and "amp;" in chunk,
            "✓ Standalone meaning": len(chunk.split()) >= 15,
            "✓ No mid-sentence truncation": not chunk.endswith(("[", "(", ",", "-"))
        }
        
        print("Quality checks:")
        for check, passed in checks.items():
            symbol = "✓" if passed else "✗"
            print(f"  {symbol} {check}")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("KNIGHT CIRCLE REVIEWS: INGESTION & CHUNKING")
    print("=" * 80 + "\n")
    
    # Load and chunk all documents
    chunks, metadata_list, total = load_and_chunk_documents("data")
    
    # Print statistics
    print(f"\nStatistics:")
    print(f"  Total chunks: {total}")
    
    if total > 0:
        avg_size = sum(len(c) for c in chunks) / len(chunks)
        print(f"  Average chunk size: {avg_size:.0f} characters")
        print(f"  Min chunk size: {min(len(c) for c in chunks)} characters")
        print(f"  Max chunk size: {max(len(c) for c in chunks)} characters")
        
        # Count by phase
        phases = {}
        for meta in metadata_list:
            phase = meta['phase']
            phases[phase] = phases.get(phase, 0) + 1
        
        print(f"\n  Chunks by phase:")
        for phase in sorted(phases.keys()):
            print(f"    {phase}: {phases[phase]} chunks")
    
    # Inspect sample chunks
    if total > 0:
        inspect_chunks(chunks, metadata_list, num_to_show=5)
    
    # Save chunks and metadata for next stage
    print("\n" + "=" * 80)
    print("Chunks ready for embedding stage!")
    print("=" * 80 + "\n")
    
    return chunks, metadata_list


if __name__ == "__main__":
    chunks, metadata_list = main()
