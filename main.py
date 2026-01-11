from src.graph import build_graph
from IPython.display import display, Markdown, Image

def main():
    print("Initializing SQL Agent...")
    app = build_graph()
    
    query = input("\nEnter your business question: ")
    initial_state = {"text": query, "iteration": 0}
    
    print("\nProcessing...")
    result = app.invoke(initial_state)
    
    print("\n" + "="*50 + "\nFINAL REPORT\n" + "="*50)
    display(Markdown(result["final_answer"]))
    
    if result.get("visualization"):
        print(f"\n[Graph Generated: {result['visualization']}]")
        # If running in terminal, just print path. If notebook, use display(Image(...))

if __name__ == "__main__":
    main()