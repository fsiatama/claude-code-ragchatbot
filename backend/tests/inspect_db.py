"""
Database Inspection Script

Checks the state of ChromaDB collections and validates data:
- Verifies collections exist
- Counts documents in each collection
- Samples documents to check formatting
- Tests search functionality
- Validates chunk context formatting
"""

import sys
import os
import io

# Set stdout to use UTF-8 encoding to handle check marks
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Add parent directory to path to import backend modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from config import config
from vector_store import VectorStore


def print_header(text):
    """Print a formatted header"""
    print("\n" + "=" * 70)
    print(f"  {text}")
    print("=" * 70)


def inspect_database():
    """Inspect ChromaDB database and print diagnostic information"""

    print_header("ChromaDB Database Inspection")
    print(f"Database Path: {config.CHROMA_PATH}")
    print(f"Embedding Model: {config.EMBEDDING_MODEL}")
    print(f"Max Results: {config.MAX_RESULTS}")

    # Initialize vector store
    try:
        vector_store = VectorStore(
            config.CHROMA_PATH,
            config.EMBEDDING_MODEL,
            config.MAX_RESULTS
        )
        print("✓ Vector store initialized successfully")
    except Exception as e:
        print(f"✗ Failed to initialize vector store: {e}")
        return

    # Check course_catalog collection
    print_header("Course Catalog Collection")
    try:
        catalog_data = vector_store.course_catalog.get()

        if catalog_data and 'ids' in catalog_data:
            num_courses = len(catalog_data['ids'])
            print(f"✓ Number of courses: {num_courses}")

            if num_courses > 0:
                print("\nCourse Titles:")
                for course_id in catalog_data['ids']:
                    print(f"  - {course_id}")

                # Sample first course metadata
                if catalog_data['metadatas']:
                    print("\nSample Course Metadata (first course):")
                    first_meta = catalog_data['metadatas'][0]
                    for key, value in first_meta.items():
                        if key != 'lessons_json':  # Skip JSON dump for readability
                            print(f"  {key}: {value}")

                    if 'lessons_json' in first_meta:
                        import json
                        lessons = json.loads(first_meta['lessons_json'])
                        print(f"  Number of lessons: {len(lessons)}")
                        if lessons:
                            print(f"  Sample lesson: {lessons[0]}")
            else:
                print("✗ No courses found in catalog!")
        else:
            print("✗ Course catalog collection is empty or malformed!")
    except Exception as e:
        print(f"✗ Error accessing course catalog: {e}")

    # Check course_content collection
    print_header("Course Content Collection")
    try:
        content_data = vector_store.course_content.get(limit=10)  # Get first 10 chunks

        if content_data and 'ids' in content_data:
            num_chunks = len(content_data['ids'])

            # Get total count
            try:
                total_data = vector_store.course_content.get()
                total_chunks = len(total_data['ids']) if total_data and 'ids' in total_data else 0
                print(f"✓ Total number of chunks: {total_chunks}")
            except:
                print(f"✓ Number of chunks (sample): {num_chunks}")

            if num_chunks > 0:
                print("\nSample Chunk Metadata:")
                for i in range(min(3, num_chunks)):
                    meta = content_data['metadatas'][i]
                    chunk_id = content_data['ids'][i]
                    print(f"\n  Chunk {i+1} (ID: {chunk_id}):")
                    print(f"    course_title: {meta.get('course_title', 'N/A')}")
                    print(f"    lesson_number: {meta.get('lesson_number', 'N/A')}")
                    print(f"    chunk_index: {meta.get('chunk_index', 'N/A')}")

                # Sample chunk content with context formatting
                print("\nSample Chunk Content (checking context formatting):")
                for i in range(min(2, num_chunks)):
                    content = content_data['documents'][i]
                    meta = content_data['metadatas'][i]
                    print(f"\n  Chunk {i+1} (Lesson {meta.get('lesson_number', 'N/A')}):")
                    print(f"    First 150 chars: {content[:150]}...")

                    # Check for context prefix
                    has_lesson_context = content.startswith("Lesson ")
                    has_course_context = content.startswith("Course ")
                    print(f"    Has 'Lesson X content:' prefix: {has_lesson_context}")
                    print(f"    Has 'Course X Lesson Y content:' prefix: {has_course_context}")

                    if not (has_lesson_context or has_course_context):
                        print(f"    ⚠ WARNING: Chunk missing expected context prefix!")
            else:
                print("✗ No content chunks found!")
        else:
            print("✗ Course content collection is empty or malformed!")
    except Exception as e:
        print(f"✗ Error accessing course content: {e}")

    # Test course name resolution
    print_header("Testing Course Name Resolution")
    try:
        # Try to resolve a partial course name
        resolved = vector_store._resolve_course_name("Building")
        if resolved:
            print(f"✓ Resolved 'Building' to: '{resolved}'")
        else:
            print("✗ Failed to resolve 'Building' to any course")

        # Try another partial name
        resolved2 = vector_store._resolve_course_name("Computer")
        if resolved2:
            print(f"✓ Resolved 'Computer' to: '{resolved2}'")
        else:
            print("✗ Failed to resolve 'Computer' to any course")
    except Exception as e:
        print(f"✗ Error testing course name resolution: {e}")

    # Test search functionality
    print_header("Testing Search Functionality")

    # Test 1: Basic search without filters
    try:
        print("\nTest 1: Basic search for 'Python'")
        results = vector_store.search(query="What is Python?", limit=3)

        if results.error:
            print(f"  ✗ Search returned error: {results.error}")
        elif results.is_empty():
            print(f"  ✗ Search returned no results")
        else:
            print(f"  ✓ Found {len(results.documents)} results")
            for i, (doc, meta) in enumerate(zip(results.documents, results.metadata)):
                print(f"\n  Result {i+1}:")
                print(f"    Course: {meta.get('course_title', 'N/A')}")
                print(f"    Lesson: {meta.get('lesson_number', 'N/A')}")
                print(f"    Distance: {results.distances[i]:.3f}")
                print(f"    Content preview: {doc[:100]}...")
    except Exception as e:
        print(f"  ✗ Search test failed: {e}")

    # Test 2: Search with course filter
    try:
        print("\nTest 2: Search with course filter")
        results = vector_store.search(
            query="computer use",
            course_name="Building",
            limit=2
        )

        if results.error:
            print(f"  ✗ Search returned error: {results.error}")
        elif results.is_empty():
            print(f"  ⚠ Search returned no results (may be expected if course name doesn't match)")
        else:
            print(f"  ✓ Found {len(results.documents)} results")
            for i, meta in enumerate(results.metadata):
                print(f"  Result {i+1}: {meta.get('course_title')} - Lesson {meta.get('lesson_number')}")
    except Exception as e:
        print(f"  ✗ Search with filter test failed: {e}")

    # Test 3: Search with lesson filter
    try:
        print("\nTest 3: Search with lesson number filter")
        results = vector_store.search(
            query="introduction",
            lesson_number=0,
            limit=2
        )

        if results.error:
            print(f"  ✗ Search returned error: {results.error}")
        elif results.is_empty():
            print(f"  ✗ Search returned no results for lesson 0")
        else:
            print(f"  ✓ Found {len(results.documents)} results from lesson 0")
            for i, meta in enumerate(results.metadata):
                lesson_num = meta.get('lesson_number')
                if lesson_num == 0:
                    print(f"  ✓ Result {i+1}: Correctly filtered to lesson 0")
                else:
                    print(f"  ✗ Result {i+1}: Wrong lesson number {lesson_num}")
    except Exception as e:
        print(f"  ✗ Search with lesson filter test failed: {e}")

    # Test get_course_outline
    print_header("Testing Course Outline Retrieval")
    try:
        outline = vector_store.get_course_outline("Building")

        if outline:
            print(f"✓ Retrieved outline for: {outline.get('course_title')}")
            print(f"  Instructor: {outline.get('instructor', 'N/A')}")
            print(f"  Course Link: {outline.get('course_link', 'N/A')}")
            lessons = outline.get('lessons', [])
            print(f"  Number of lessons: {len(lessons)}")
            if lessons:
                print(f"  First lesson: {lessons[0]}")
                print(f"  Last lesson: {lessons[-1]}")
        else:
            print("✗ Failed to retrieve course outline")
    except Exception as e:
        print(f"✗ Error testing course outline: {e}")

    # Summary
    print_header("Inspection Summary")
    print("\nKey Findings:")

    try:
        catalog_count = len(vector_store.course_catalog.get()['ids'])
        content_count = len(vector_store.course_content.get()['ids'])

        if catalog_count == 0:
            print("  ✗ CRITICAL: No courses in catalog collection - database may be empty!")
        elif catalog_count < 3:
            print(f"  ⚠ WARNING: Only {catalog_count} course(s) in catalog (expected 4)")
        else:
            print(f"  ✓ Catalog has {catalog_count} courses")

        if content_count == 0:
            print("  ✗ CRITICAL: No content chunks - database may be empty!")
        else:
            print(f"  ✓ Content collection has {content_count} chunks")
            avg_chunks_per_course = content_count / catalog_count if catalog_count > 0 else 0
            print(f"    Average chunks per course: {avg_chunks_per_course:.1f}")

        # Test a simple search
        test_results = vector_store.search("lesson", limit=1)
        if test_results.is_empty():
            print("  ✗ CRITICAL: Search returns no results - semantic search may be broken!")
        else:
            print("  ✓ Basic search functionality working")

    except Exception as e:
        print(f"  ✗ Error generating summary: {e}")

    print("\n" + "=" * 70 + "\n")


if __name__ == "__main__":
    inspect_database()
