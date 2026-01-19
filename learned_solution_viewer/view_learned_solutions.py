"""
view_learned_solutions.py - View All Learned Solutions

Displays all learned solutions stored in ChromaDB.
"""

import sys
sys.path.insert(0, '.')

from backend.tools.rag_tool import RAGTool
from datetime import datetime

def view_learned_solutions():
    """Display all learned solutions."""
    print("=" * 80)
    print("LEARNED SOLUTIONS VIEWER")
    print("=" * 80)
    
    # Initialize RAG
    rag = RAGTool()
    rag.initialize()
    
    # Get all solution IDs
    solution_ids = rag.get_all_learned_solutions()
    
    if not solution_ids:
        print("\n⚠️ No learned solutions found")
        print("\nTo add solutions, run successful test executions.")
        return
    
    print(f"\n📊 Found {len(solution_ids)} learned solution(s)\n")
    print("=" * 80)
    
    # Display each solution
    for i, test_id in enumerate(solution_ids, 1):
        solution = rag.get_learned_solution(test_id)
        
        if not solution:
            continue
        
        print(f"\n{i}. TEST ID: {solution['test_id']}")
        print(f"   Title: {solution['title']}")
        print(f"   Component: {solution['component']}")
        print(f"   " + "-" * 70)
        
        # Success metrics
        print(f"   ✓ Executions: {solution['execution_count']}")
        print(f"   ✓ Successes: {solution['success_count']}")
        print(f"   ✓ Success Rate: {solution['success_rate']:.0%}")
        
        # Timestamps
        try:
            created = datetime.fromisoformat(solution['created_at'])
            last_exec = datetime.fromisoformat(solution['last_execution'])
            print(f"   ✓ Created: {created.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"   ✓ Last Execution: {last_exec.strftime('%Y-%m-%d %H:%M:%S')}")
        except:
            print(f"   ✓ Created: {solution['created_at']}")
            print(f"   ✓ Last Execution: {solution['last_execution']}")
        
        # Steps
        print(f"\n   Steps ({len(solution['steps'])}):")
        for step in solution['steps']:
            print(f"      {step.get('step', '?')}. {step.get('action', 'unknown').upper()}", end="")
            
            if step.get('coordinates'):
                print(f" @ ({step['coordinates'][0]}, {step['coordinates'][1]})", end="")
            
            if step.get('target_element'):
                print(f" → {step['target_element']}", end="")
            
            if step.get('input_text'):
                print(f" (input: '{step['input_text']}')", end="")
            
            if step.get('description'):
                print(f"\n         {step['description']}", end="")
            
            print()  # New line
        
        print("   " + "-" * 70)
    
    print("\n" + "=" * 80)
    print(f"Total: {len(solution_ids)} learned solutions")
    print("=" * 80)


if __name__ == "__main__":
    try:
        view_learned_solutions()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)