"""
edit_learned_solutions.py - Edit Learned Solutions

Provides interactive editing of learned solutions.
"""

import sys
sys.path.insert(0, '.')

from backend.tools.rag_tool import RAGTool

def list_solutions(rag):
    """List all learned solutions."""
    solution_ids = rag.get_all_learned_solutions()
    
    if not solution_ids:
        print("\n⚠️ No learned solutions found")
        return []
    
    print(f"\n📋 Found {len(solution_ids)} learned solution(s):\n")
    
    for i, test_id in enumerate(solution_ids, 1):
        solution = rag.get_learned_solution(test_id)
        if solution:
            print(f"{i}. {test_id}")
            print(f"   Title: {solution['title']}")
            print(f"   Success Rate: {solution['success_rate']:.0%} ({solution['success_count']}/{solution['execution_count']})")
            print()
    
    return solution_ids


def view_solution(rag, test_id):
    """View detailed solution."""
    solution = rag.get_learned_solution(test_id)
    
    if not solution:
        print(f"❌ Solution not found: {test_id}")
        return
    
    print("\n" + "=" * 80)
    print(f"TEST ID: {solution['test_id']}")
    print("=" * 80)
    print(f"Title: {solution['title']}")
    print(f"Component: {solution['component']}")
    print(f"Success Rate: {solution['success_rate']:.0%} ({solution['success_count']}/{solution['execution_count']})")
    print(f"Created: {solution['created_at']}")
    print(f"Last Execution: {solution['last_execution']}")
    
    print(f"\nSteps ({len(solution['steps'])}):")
    for step in solution['steps']:
        print(f"  {step.get('step', '?')}. {step.get('action', 'unknown').upper()}", end="")
        if step.get('coordinates'):
            print(f" @ {step['coordinates']}", end="")
        if step.get('target_element'):
            print(f" → {step['target_element']}", end="")
        if step.get('description'):
            print(f"\n     {step['description']}", end="")
        print()
    print("=" * 80)


def delete_solution(rag, test_id):
    """Delete a learned solution."""
    print(f"\n⚠️  About to delete solution: {test_id}")
    confirm = input("Are you sure? (yes/no): ").strip().lower()
    
    if confirm != 'yes':
        print("❌ Cancelled")
        return
    
    try:
        # Delete from ChromaDB
        rag.learned_solutions_collection.delete(ids=[test_id])
        print(f"✅ Deleted solution: {test_id}")
    except Exception as e:
        print(f"❌ Delete error: {e}")


def update_solution(rag, test_id):
    """Update a learned solution."""
    solution = rag.get_learned_solution(test_id)
    
    if not solution:
        print(f"❌ Solution not found: {test_id}")
        return
    
    print(f"\n📝 Editing solution: {test_id}")
    print("=" * 80)
    
    # Edit title
    print(f"\nCurrent title: {solution['title']}")
    new_title = input("New title (press Enter to keep): ").strip()
    if new_title:
        solution['title'] = new_title
    
    # Edit component
    print(f"\nCurrent component: {solution['component']}")
    new_component = input("New component (press Enter to keep): ").strip()
    if new_component:
        solution['component'] = new_component
    
    # Edit steps
    print(f"\nCurrent steps: {len(solution['steps'])}")
    print("Do you want to edit steps? (yes/no): ", end="")
    if input().strip().lower() == 'yes':
        solution['steps'] = edit_steps(solution['steps'])
    
    # Save updated solution
    print("\n💾 Saving changes...")
    success = rag.save_learned_solution(
        test_id=solution['test_id'],
        title=solution['title'],
        component=solution['component'],
        steps=solution['steps']
    )
    
    if success:
        print("✅ Solution updated successfully!")
    else:
        print("❌ Failed to update solution")


def edit_steps(steps):
    """Edit steps interactively."""
    print("\n📝 Editing steps...")
    print("Current steps:")
    
    for i, step in enumerate(steps, 1):
        print(f"\n{i}. Action: {step.get('action', 'unknown')}")
        if step.get('coordinates'):
            print(f"   Coordinates: {step['coordinates']}")
        if step.get('target_element'):
            print(f"   Target: {step['target_element']}")
        if step.get('description'):
            print(f"   Description: {step['description']}")
    
    print("\nOptions:")
    print("1. Keep all steps")
    print("2. Edit specific step")
    print("3. Delete step")
    print("4. Add new step")
    
    choice = input("\nChoice (1-4): ").strip()
    
    if choice == '1':
        return steps
    elif choice == '2':
        step_num = int(input("Step number to edit: ")) - 1
        if 0 <= step_num < len(steps):
            steps[step_num] = edit_single_step(steps[step_num])
    elif choice == '3':
        step_num = int(input("Step number to delete: ")) - 1
        if 0 <= step_num < len(steps):
            del steps[step_num]
            # Renumber steps
            for i, step in enumerate(steps, 1):
                step['step'] = i
    elif choice == '4':
        new_step = create_new_step(len(steps) + 1)
        steps.append(new_step)
    
    return steps


def edit_single_step(step):
    """Edit a single step."""
    print(f"\nEditing step {step.get('step', '?')}")
    
    # Action
    print(f"Current action: {step.get('action', 'unknown')}")
    new_action = input("New action (tap/swipe/input_text/verify) [Enter to keep]: ").strip()
    if new_action:
        step['action'] = new_action
    
    # Coordinates
    if step['action'] in ['tap', 'swipe']:
        print(f"Current coordinates: {step.get('coordinates', 'none')}")
        coords = input("New coordinates (x,y) [Enter to keep]: ").strip()
        if coords:
            x, y = map(int, coords.split(','))
            step['coordinates'] = [x, y]
    
    # Target element
    print(f"Current target: {step.get('target_element', 'none')}")
    new_target = input("New target element [Enter to keep]: ").strip()
    if new_target:
        step['target_element'] = new_target
    
    # Description
    print(f"Current description: {step.get('description', 'none')}")
    new_desc = input("New description [Enter to keep]: ").strip()
    if new_desc:
        step['description'] = new_desc
    
    return step


def create_new_step(step_num):
    """Create a new step."""
    print(f"\nCreating new step {step_num}")
    
    action = input("Action (tap/swipe/input_text/verify): ").strip()
    
    step = {
        'step': step_num,
        'action': action,
        'success': True
    }
    
    if action in ['tap', 'swipe']:
        coords = input("Coordinates (x,y): ").strip()
        x, y = map(int, coords.split(','))
        step['coordinates'] = [x, y]
    
    target = input("Target element [optional]: ").strip()
    if target:
        step['target_element'] = target
    
    desc = input("Description [optional]: ").strip()
    if desc:
        step['description'] = desc
    
    if action == 'input_text':
        text = input("Input text: ").strip()
        step['input_text'] = text
    
    return step


def add_new_solution(rag):
    """Add a completely new learned solution."""
    print("\n➕ Adding new learned solution")
    print("=" * 80)
    
    test_id = input("Test ID: ").strip()
    title = input("Title: ").strip()
    component = input("Component: ").strip()
    
    print("\nAdding steps (type 'done' when finished)...")
    steps = []
    step_num = 1
    
    while True:
        print(f"\nStep {step_num}:")
        action = input("  Action (tap/swipe/input_text/verify) or 'done': ").strip()
        
        if action == 'done':
            break
        
        step = {
            'step': step_num,
            'action': action,
            'success': True
        }
        
        if action in ['tap', 'swipe']:
            coords = input("  Coordinates (x,y): ").strip()
            x, y = map(int, coords.split(','))
            step['coordinates'] = [x, y]
        
        target = input("  Target element [optional]: ").strip()
        if target:
            step['target_element'] = target
        
        desc = input("  Description [optional]: ").strip()
        if desc:
            step['description'] = desc
        
        if action == 'input_text':
            text = input("  Input text: ").strip()
            step['input_text'] = text
        
        steps.append(step)
        step_num += 1
    
    if steps:
        print("\n💾 Saving new solution...")
        success = rag.save_learned_solution(
            test_id=test_id,
            title=title,
            component=component,
            steps=steps
        )
        
        if success:
            print(f"✅ Added new solution: {test_id}")
        else:
            print("❌ Failed to save solution")
    else:
        print("❌ No steps added, cancelled")


def main():
    """Main interactive menu."""
    print("=" * 80)
    print("LEARNED SOLUTIONS EDITOR")
    print("=" * 80)
    
    # Initialize RAG
    rag = RAGTool()
    rag.initialize()
    
    while True:
        print("\n" + "=" * 80)
        print("MENU")
        print("=" * 80)
        print("1. List all solutions")
        print("2. View solution details")
        print("3. Update solution")
        print("4. Delete solution")
        print("5. Add new solution")
        print("6. Exit")
        
        choice = input("\nChoice (1-6): ").strip()
        
        if choice == '1':
            list_solutions(rag)
            
        elif choice == '2':
            test_id = input("Enter test ID: ").strip()
            view_solution(rag, test_id)
            
        elif choice == '3':
            solution_ids = list_solutions(rag)
            if solution_ids:
                test_id = input("\nEnter test ID to update: ").strip()
                update_solution(rag, test_id)
            
        elif choice == '4':
            solution_ids = list_solutions(rag)
            if solution_ids:
                test_id = input("\nEnter test ID to delete: ").strip()
                delete_solution(rag, test_id)
            
        elif choice == '5':
            add_new_solution(rag)
            
        elif choice == '6':
            print("\n👋 Goodbye!")
            break
        
        else:
            print("❌ Invalid choice")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)