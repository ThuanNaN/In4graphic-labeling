import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime

API_URL = "http://localhost:8000"

st.set_page_config(
    page_title="Infographics Labeling Tool",
    page_icon="🏷️",
    layout="wide"
)

def main():
    st.title("Infographics Labeling Tool")
    
    # Initialize session state
    if 'current_index' not in st.session_state:
        st.session_state.current_index = 0
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = None
    
    # Sidebar
    st.sidebar.header("Navigation")
    page = st.sidebar.radio("Choose a page", ["Category Selection", "Label Infographics", "View Labels", "Data Management"])
    
    # Reload data button in sidebar
    if st.sidebar.button("🔄 Reload Data"):
        response = requests.get(f"{API_URL}/reload-data")
        if response.status_code == 200:
            st.sidebar.success("Data reloaded successfully!")
        else:
            st.sidebar.error("Failed to reload data")
    
    if page == "Category Selection":
        select_category()
    elif page == "Label Infographics":
        if st.session_state.selected_category:
            label_infographics()
        else:
            st.warning("Please select a category first!")
            select_category()
    elif page == "View Labels":
        view_labels()
    else:
        data_management()

def select_category():
    st.header("Select Category to Label")
    
    # Get category statistics
    response = requests.get(f"{API_URL}/category-stats")
    if response.status_code == 200:
        stats = response.json()
        
        # Create a DataFrame for better display
        df = pd.DataFrame.from_dict(stats, orient='index')
        
        # Display category statistics
        st.subheader("Category Statistics")
        
        # Create columns for each category
        cols = st.columns(len(stats))
        for idx, (category, data) in enumerate(stats.items()):
            with cols[idx]:
                st.metric(
                    label=category,
                    value=f"{data['labeled']}/{data['total']}",
                    delta=f"{data['unlabeled']} remaining"
                )
        
        # Category selection
        selected = st.selectbox(
            "Select Category to Label",
            options=list(stats.keys()),
            format_func=lambda x: f"{x} ({stats[x]['unlabeled']} unlabeled)"
        )
        
        if st.button("Start Labeling"):
            st.session_state.selected_category = selected
            st.session_state.current_index = 0
            st.success(f"Selected category: {selected}")
            st.rerun()

def label_infographics():
    st.header(f"Labeling Category: {st.session_state.selected_category}")
    
    # Add button to change category
    if st.button("Change Category"):
        st.session_state.selected_category = None
        st.rerun()
    
    # Fetch unlabeled infographics for selected category
    response = requests.get(
        f"{API_URL}/infographics/unlabeled",
        params={"category": st.session_state.selected_category}
    )
    
    if response.status_code == 200:
        infographics = response.json()
        
        if not infographics:
            st.success(f"All images in category '{st.session_state.selected_category}' have been labeled!")
            if st.button("Select Another Category"):
                st.session_state.selected_category = None
                st.rerun()
            return
        
        # Navigation buttons
        col1, col2, col3 = st.columns([1,3,1])
        with col1:
            if st.button("⬅️ Previous") and st.session_state.current_index > 0:
                st.session_state.current_index -= 1
        with col2:
            st.write(f"Image {st.session_state.current_index + 1} of {len(infographics)}")
        with col3:
            if st.button("Next ➡️") and st.session_state.current_index < len(infographics) - 1:
                st.session_state.current_index += 1
        
        # Display current infographic
        current = infographics[st.session_state.current_index]
        
        # Display image and info in columns
        col1, col2 = st.columns([1,1])
        
        with col1:
            st.image(current["img_url"], caption=current["title"])
            
        with col2:
            st.subheader("Original Information")
            st.write(f"**Category:** {current['category']}")
            st.write(f"**Description:** {current['description']}")
            st.write("**Tags:**")
            for tag in current['tags']:
                if tag:  # Only display non-empty tags
                    st.write(f"- {tag}")
            
            st.subheader("Label Information")
            with st.form(key=f"label_form_{st.session_state.current_index}"):
                # Tags input
                tags = st.text_area("Tags (one per line)", "\n".join(filter(None, current['tags'])))
                
                # VQA Section
                st.subheader("Visual Question Answering")
                
                # Initialize session state for QA pairs if not exists
                if 'qa_pairs' not in st.session_state:
                    st.session_state.qa_pairs = [{"question": "", "answer": ""}]
                
                # Display existing QA pairs
                qa_pairs = []
                for i in range(len(st.session_state.qa_pairs)):
                    st.markdown(f"**QA Pair {i+1}**")
                    col1, col2 = st.columns(2)
                    # with col1:
                    question = st.text_input(
                        label=f"Question {i+1}",
                        value=st.session_state.qa_pairs[i]["question"],
                        key=f"q_{i}"
                    )
                    # with col2:
                    answer = st.text_input(
                        f"Answer {i+1}",
                        value=st.session_state.qa_pairs[i]["answer"],
                        key=f"a_{i}"
                    )
                    st.divider()
                    qa_pairs.append({"question": question, "answer": answer})
                
                # Add/Remove QA pair buttons
                col1, col2 = st.columns(2)
                with col1:
                    add_qa_pair = st.form_submit_button("➕ Add QA Pair")
                with col2:
                    remove_qa_pair = st.form_submit_button("➖ Remove Last Pair")

                if add_qa_pair:
                    st.session_state.qa_pairs.append({"question": "", "answer": ""})
                    st.rerun()

                if remove_qa_pair and len(st.session_state.qa_pairs) > 1:
                    st.session_state.qa_pairs.pop()
                    st.rerun()
                
                # Submit button
                if st.form_submit_button("Submit Label"):
                    # Filter out empty QA pairs
                    valid_qa_pairs = [
                        qa for qa in qa_pairs 
                        if qa["question"].strip() and qa["answer"].strip()
                    ]
                    
                    if not valid_qa_pairs:
                        st.error("Please add at least one valid question-answer pair")
                        return
                    
                    label_data = {
                        "infographic_title": current["title"],
                        "category": st.session_state.selected_category,
                        "tags": [tag.strip() for tag in tags.split("\n") if tag.strip()],
                        "qa_pairs": valid_qa_pairs,
                        "labeled_by": "user",
                        "labeled_at": datetime.now().isoformat()
                    }
                    
                    response = requests.post(f"{API_URL}/labels", json=label_data)
                    if response.status_code == 200:
                        st.success("Label submitted successfully!")
                        # Reset QA pairs for next image
                        st.session_state.qa_pairs = [{"question": "", "answer": ""}]
                        # Move to next image if available
                        if st.session_state.current_index < len(infographics) - 1:
                            st.session_state.current_index += 1
                            st.rerun()
                    else:
                        st.error("Failed to submit label.")


def view_labels():
    st.header("View Labels")
    
    # Category filter for labels
    categories_response = requests.get(f"{API_URL}/categories")
    if categories_response.status_code == 200:
        categories = ["All"] + categories_response.json()
        selected_category = st.selectbox("Filter by Category", categories)
    
    # Fetch labels
    params = {"category": selected_category} if selected_category != "All" else None
    response = requests.get(f"{API_URL}/labels", params=params)
    
    if response.status_code == 200:
        labels = response.json()
        if labels:
            # Process the data to make it more readable
            processed_labels = []
            for label in labels:
                # Format QA pairs for display
                qa_formatted = "\n".join([
                    f"Q{i+1}: {qa['question']}\nA{i+1}: {qa['answer']}"
                    for i, qa in enumerate(label['qa_pairs'])
                ])
                
                processed_label = {
                    "Title": label["infographic_title"],
                    "Category": label["category"],
                    "Tags": ", ".join(label["tags"]),
                    "QA Pairs": qa_formatted,
                    "Labeled By": label["labeled_by"],
                    "Labeled At": label["labeled_at"]
                }
                processed_labels.append(processed_label)
            
            df = pd.DataFrame(processed_labels)
            st.dataframe(df)
            
            # Export buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Export to CSV"):
                    df.to_csv("labels_export.csv", index=False)
                    st.success("Labels exported to CSV!")
            with col2:
                if st.button("Export to JSON"):
                    # Convert back to original format for JSON export
                    json_data = labels
                    with open("labels_export.json", "w", encoding="utf-8") as f:
                        json.dump(json_data, f, ensure_ascii=False, indent=2)
                    st.success("Labels exported to JSON!")
        else:
            st.info("No labels recorded yet.")
    else:
        st.error("Failed to fetch labels.")


def data_management():
    st.header("Data Management")
    
    # Display category statistics
    response = requests.get(f"{API_URL}/category-stats")
    if response.status_code == 200:
        stats = response.json()
        
        st.subheader("Labeling Progress")
        
        # Create progress bars for each category
        for category, data in stats.items():
            col1, col2 = st.columns([3, 1])
            with col1:
                progress = data['labeled'] / data['total']
                st.progress(progress)
            with col2:
                st.write(f"{category}: {data['labeled']}/{data['total']}")
        
        # Overall statistics
        total_images = sum(data['total'] for data in stats.values())
        total_labeled = sum(data['labeled'] for data in stats.values())
        
        st.subheader("Overall Progress")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Images", total_images)
        with col2:
            st.metric("Labeled Images", total_labeled)
        with col3:
            st.metric("Remaining", total_images - total_labeled)

if __name__ == "__main__":
    main()