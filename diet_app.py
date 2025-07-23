import json
import streamlit as st
import google.generativeai as genai
import math
import pandas as pd

import warnings
warnings.filterwarnings("ignore")

#Setup & Authentication
GOOGLE_API_KEY = "AIzaSyDDV2rsBI9KE31RcD89SK-SIFlce-K-2OM"

# Configure Gemini
client = genai.configure(api_key=GOOGLE_API_KEY)

model = genai.GenerativeModel(
    model_name="models/gemini-2.0-flash",
    generation_config={
        "temperature": 0.7,
        "top_p": 1,
        "top_k": 1,
        "max_output_tokens": 2048,
        "response_mime_type": "application/json"  # ensures structured JSON output
    }
)

st.set_page_config(page_title="NutriGenie: Your Personalized Diet Planner", layout="centered")

st.title("NutriGenie: Your Personalized Diet Planner 🥗")
st.markdown("Get a diet chart tailored to your body and lifestyle.")

with st.form("user_form"):
    st.subheader("Let’s get to know you a bit!")
    age = st.number_input("Age", min_value=10, max_value=100)
    gender = st.selectbox("Gender (We ask because nutrition needs can vary)", ["Male", "Female", "Non Binary", "Other/Prefer to describe", "Prefer not to say"])
    height_cm = st.number_input("Height (in cm)", min_value=100, max_value=250)
    weight_lbs = st.number_input("Weight (in lbs)", min_value=70, max_value=500)

    st.subheader("Dietary Preferences")
    dietary_pref = st.selectbox("Macro Diet Type", ["None", "Vegetarian", "Vegan", "Eggetarian", "Other (please specify)"])
    other_diet = ""
    # Show the text input immediately when 'Other (please specify)' is selected
    if dietary_pref == "Other (please specify)":
        other_diet = st.text_input("Please specify your dietary preference", key="other_diet_input")

    cuisine_pref = st.text_input("Preferred Cuisine Style (e.g., Oriental, Mediterranean, Continental, etc.)")

    allergies = st.text_input("Any allergies? (comma separated)")
    medical_conditions = st.text_input("Medical Conditions (comma separated)")
    exercise = st.selectbox("Exercise Routine", ["None", "Light (1-2 days/week)", "Moderate (3-4 days/week)", "Heavy (5+ days/week)"])

    st.subheader("More About You!")
    body_fat = st.number_input("Body Fat %", min_value=0.0, max_value=60.0, step=0.1)
    visceral_fat = st.number_input("Visceral Fat %", min_value=0.0, max_value=50.0, step=0.1)
    muscle_mass = st.number_input("Muscle Mass (in lbs)", min_value=0.0, max_value=300.0, step=0.1)
    rmr = st.number_input("Resting Metabolic Rate (RMR)", min_value=0.0, max_value=5000.0, step=1.0)

    st.subheader("📅 Plan Duration")
    duration_option = st.selectbox("Choose how many days you want the meal plan for:", ["1 Day", "1 Week", "1 Month", "Custom"])
    num_days = 1
    if duration_option == "1 Week":
        num_days = 7
    elif duration_option == "1 Month":
        num_days = 30
    elif duration_option == "Custom":
        num_days = st.number_input("Enter number of days", min_value=1, max_value=60, step=1, key="custom_num_days")

    # Only show body measurements if user did not input body fat, visceral fat, muscle mass, and rmr
    show_body_measurements = not all([body_fat, visceral_fat, muscle_mass, rmr])
    neck = waist = hip = None
    if show_body_measurements:
        st.subheader("Body Measurements for Estimation")
        neck = st.number_input("Neck Circumference (in cm)", min_value=20.0, max_value=60.0, step=0.1)
        waist = st.number_input("Waist Circumference (in cm)", min_value=40.0, max_value=200.0, step=0.1)
        if gender == "Female":
            hip = st.number_input("Hip Circumference (in cm)", min_value=40.0, max_value=200.0, step=0.1)

    submitted = st.form_submit_button("Generate My Plan")

   
    def calculate_bmi_bmr(height_cm, weight_kg, age, gender):
        """
        Function to calculate BMI and BMR using Gemini API.
        """
        # Define the prompt for the Gemini API
        prompt = f"""
        You are a health assistant. Calculate the BMI and BMR for the following user:
    
        - Height: {height_cm} cm
        - Weight: {weight_kg} kg
        - Age: {age} years
        - Gender: {gender}
    
        Instructions:
        - BMI = weight (kg) / (height (m)^2)
        - BMR formula:
        - For males: BMR = 10 * weight (kg) + 6.25 * height (cm) - 5 * age + 5
        - For females: BMR = 10 * weight (kg) + 6.25 * height (cm) - 5 * age - 161
        - Respond with a JSON object containing "BMI" and "BMR".
        """

        try:
            # Call the Gemini API
            response = model.generate_content(prompt)
            result = json.loads(response.text)  # Parse the JSON response
            return result["BMI"], result["BMR"]
        except Exception as e:
            st.error(f"Error calculating BMI/BMR: {e}")
            return None, None


    def calculate_estimates():
        weight_kg = weight_lbs * 0.453592
        height_m = height_cm / 100

        if gender == "Male":
            bf = 495 / (1.0324 - 0.19077 * math.log10(waist - neck) +
                        0.15456 * math.log10(height_cm)) - 450
        else:
            bf = 495 / (1.29579 - 0.35004 * math.log10(waist + hip - neck) +
                        0.22100 * math.log10(height_cm)) - 450

        whr = waist / hip if hip else waist / height_cm
        vf = round((whr * 10), 2)

        lean_mass = weight_kg * (1 - bf / 100)
        mm = round(lean_mass * 2.20462, 2)  # in lbs

        if gender == "Male":
            rmr_val = 10 * weight_kg + 6.25 * height_cm - 5 * age + 5
        else:
            rmr_val = 10 * weight_kg + 6.25 * height_cm - 5 * age - 161

        return round(bf, 2), vf, mm, round(rmr_val, 2), round(age + (bf - 15) / 2, 1)


if submitted:
    # Convert weight to kg (if input is in lbs)
    weight_kg = weight_lbs * 0.453592

    # Call the function to calculate BMI and BMR using Gemini API
    bmi, bmr = calculate_bmi_bmr(height_cm, weight_kg, age, gender)

    if not all([body_fat, visceral_fat, muscle_mass, rmr]):
        body_fat, visceral_fat, muscle_mass, rmr, body_age = calculate_estimates()
    else:
        body_age = round(age + (body_fat - 15) / 2, 1)

    final_diet_pref = other_diet if dietary_pref == "Other (please specify)" else dietary_pref

    # Display health stats
    st.subheader("📋 Your Health Snapshot")
    st.write(f"**Body Fat %**: {body_fat}%")
    st.write(f"**Visceral Fat Level**: {visceral_fat}")
    st.write(f"**Muscle Mass**: {muscle_mass} lbs")
    st.write(f"**RMR**: {rmr} kcal")
    st.write(f"**Body Age**: {body_age} years")

    # Display BMI and BMR if calculated successfully
    if bmi and bmr:
        try:
            # Convert BMI and BMR to float before formatting
            bmi = float(bmi)
            bmr = float(bmr)
            st.write(f"**BMI**: {bmi:.2f}")
            st.write(f"**BMR**: {bmr:.2f} kcal/day")
        except ValueError:
            st.error("Could not format BMI or BMR. Please check the API response.")
    else:
        st.error("Could not calculate BMI and BMR.")

    st.subheader("🥗 Generating Meal Plan...")

    daily_plans = []
    for day in range(num_days):
        # Dynamically include "After Workout" meal only if the user exercises
        meal_instructions = """
        - Include meals: On Rising, Mid Morning, Lunch, Evening Snack, Dinner
        """
        if exercise != "None":
            meal_instructions = """
            - Include meals: On Rising, After Workout, Mid Morning, Lunch, Evening Snack, Dinner
            """

        # Generate a unique prompt for each day
        prompt = f"""You are a nutritionist. Create a detailed day-{day+1} diet chart based on these user inputs:

        Age: {age}
        Gender: {gender}
        Height: {height_cm} cm
        Weight: {weight_lbs} lbs
        Dietary Preference: {final_diet_pref}
        Cuisine Style Preference: {cuisine_pref}
        Allergies: {allergies}
        Medical Conditions: {medical_conditions}
        Exercise Routine: {exercise}
        Body Fat %: {body_fat}
        Visceral Fat Level: {visceral_fat}
        Muscle Mass (lbs): {muscle_mass}
        RMR: {rmr}
        Body Age: {body_age}

        Instructions:
        - Provide a full-day meal plan with weights/quantities (e.g. 2 raisins, 3 almonds, 30 gm oats, 200 ml milk)
        {meal_instructions}
        - Do not include any food items that the user is allergic to
        - Ensure the meal plan is balanced and nutritious
        - Include a variety of food items to avoid monotony
        - Ensure the meal plan is suitable for the specified dietary preference
        - Ensure the meal plan is suitable for the specified cuisine style
        - Ensure the meal plan is suitable for the specified exercise routine
        - Include calories per meal
        - Format output as a table with columns: Meal Time | Food Items | Calories
        - Respond only with the table and total calorie count.
        """

        try:
            # Generate content for the current day
            response = model.generate_content(prompt)
            plan_text = response.text  # Ensure this is updated for each day
            daily_plans.append((f"Day {day+1}", plan_text))
        except Exception as e:
            st.error(f"Error generating Day {day+1} meal plan: {e}")

    if daily_plans:
        st.subheader("📋 Your Meal Plans")
        # Iterate over the daily plans and display the day. For each day, display the meal plan in a table format.
        for day_index, (day, plan_text) in enumerate(daily_plans, start=1):
            st.markdown(f"### {day}")
            try:
                # Convert the plan text into a DataFrame for better display
                plan_data = json.loads(plan_text)
                plan_df = pd.DataFrame(plan_data, columns=["Meal Time", "Food Items", "Calories"])

                # Remove any rows where all columns are None or empty (e.g., trailing row after dinner)
                plan_df = plan_df.dropna(how="all")
                plan_df = plan_df[~((plan_df["Meal Time"].isnull() | (plan_df["Meal Time"] == "")) &
                                   (plan_df["Food Items"].isnull() | (plan_df["Food Items"] == "")) &
                                   (plan_df["Calories"].isnull() | (plan_df["Calories"] == "")))]

                # Remove the 'Total Calories' row from the table if present
                plan_df["Meal Time"] = plan_df["Meal Time"].astype(str)
                plan_df = plan_df[plan_df["Meal Time"].str.lower() != "total calories"]

                # Convert the "Calories" column to numeric for summation
                plan_df["Calories"] = pd.to_numeric(plan_df["Calories"], errors="coerce")

                # Calculate total calories
                total_calories = plan_df["Calories"].sum()

                # Display the DataFrame without the index
                st.dataframe(plan_df, use_container_width=True, hide_index=True)

                # Display the total calories below the table
                st.write(f"**Total Calories for Day {day_index}: {total_calories:.2f} kcal**")
            except Exception as e:
                st.error(f"Could not display meal plan for Day {day_index}: {e}")