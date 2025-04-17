# Dream Script Backend

A Flask-based backend API for journaling, analyzing, and exploring dreams. This project provides endpoints for storing dream entries, performing NLP analysis (type detection, sentiment, symbol extraction), calculating 'Dream DNA', looking up symbol meanings, generating reflections, and more.

## Features

* **Dream Journaling:** Add, retrieve, update, and delete dream entries.
* **NLP Analysis:** Automatically analyzes dreams upon submission for:
    * **Dream Type:** Detects basic types like Normal, Nightmare, Lucid.
    * **Emotional Tone:** Calculates sentiment scores using VADER.
    * **Symbol Extraction:** Identifies common dream symbols from text.
* **Symbol Guide:** API endpoint to retrieve potential meanings for identified symbols. (Includes personal frequency tracking).
* **Dream DNA:** Calculates a breakdown of a dream's emotional and thematic composition (based on keywords).
* **Longitudinal Analysis:**
    * Generates simple reflection points based on recent dream patterns.
    * Provides data structured for an emotion timeline visualization.
* **Search & Filter:** Search dream text and filter journal entries by date range, emotion, or symbols.
* **Enhancements:**
    * "Dreamify" feature to generate simple poetic or noir snippets from dreams.
    * Basic recommendations based on dream emotion.
* **Data Export:** Export user's dream journal to a CSV file.

## Technology Stack

* **Language:** Python 3
* **Framework:** Flask
* **Data Handling:** Pandas (Currently using CSV files for storage - **Database migration recommended**)
* **NLP:** spaCy (for tokenization/lemmatization), NLTK (for VADER sentiment analysis)
* **Environment:** Virtual Environment (`venv`)

## Setup Instructions

1.  **Clone the Repository:**
    ```bash
    git clone [https://github.com/your-username/dream-decoder-backend.git](https://github.com/your-username/dream-decoder-backend.git) # Replace with your repo URL
    cd dream-decoder-backend
    ```

2.  **Create and Activate Virtual Environment:**
    ```bash
    # Create
    python3 -m venv .venv
    # Activate (macOS/Linux)
    source .venv/bin/activate
    # Activate (Windows)
    # .venv\Scripts\activate
    ```

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Download NLP Models:**
    ```bash
    python3 -m spacy download en_core_web_sm
    python3 -c "import nltk; nltk.download('vader_lexicon')"
    # See troubleshooting steps in setup guide if SSL errors occur
    ```

5.  **Configuration (Optional):**
    * The application looks for CSV files (`dream_journal.csv`, `symbol_guide.csv`) in a `data/` subdirectory by default.
    * A secret key is set in `app/__init__.py` - consider setting this via environment variables for production.

## Running the Application

1.  **Ensure Virtual Environment is Active:** (`(.venv)` should be visible in your terminal prompt).
2.  **Run the Flask Development Server:**
    ```bash
    python3 run.py
    ```
3.  The API should now be running, typically at `http://127.0.0.1:5001`. Check the terminal output for the exact URL.

## API Endpoints Overview

* `GET /api/status`: Check if the API is running.
* `POST /api/dreams`: Add a new dream. (Body: `{"user_id", "dream_text", "dream_date"}`)
* `GET /api/dreams`: Get dreams for a user, with optional search/filter query parameters (`user_id`, `search_term`, `start_date`, `end_date`, `emotion`, `symbol`).
* `GET /api/dreams/<dream_id>`: Get a specific dream.
* `PUT /api/dreams/<dream_id>`: Update a dream. (Body: `{"dream_text"?, "dream_date"?}`)
* `DELETE /api/dreams/<dream_id>`: Delete a dream.
* `GET /api/symbols/<symbol_name>`: Get symbol details (add `?user_id=` for personal stats).
* `GET /api/dreams/<dream_id>/dna`: Get Dream DNA analysis.
* `GET /api/reflections?user_id=...[&days=...]`: Get reflections for a user.
* `GET /api/timeline?user_id=...[&start_date=...&end_date=...]`: Get data for emotion timeline.
* `POST /api/dreams/<dream_id>/dreamify?style=...`: Get stylized text from a dream.
* `GET /api/dreams/<dream_id>/recommendations`: Get recommendations for a dream.
* `GET /api/export?user_id=...`: Export user's journal as CSV.

*(Refer to `app/routes.py` for detailed parameter requirements).*

## Testing

Use an API client like [Postman](https://www.postman.com/) or [Insomnia](https://insomnia.rest/) to send requests to the running API endpoints.

## Future Work / TODOs

* **Migrate to Database:** Replace CSV file storage with SQLite (using SQLAlchemy or similar ORM) or a more robust database like PostgreSQL for better scalability and data integrity.
* **Refine NLP:** Improve accuracy of type detection, sentiment analysis, and especially theme/symbol extraction.
* **Add User Authentication:** Implement proper user registration and login.
* **Improve Error Handling:** Add more specific error responses and logging.
* **Add Unit/Integration Tests:** Create a test suite (`tests/` folder).
* **API Documentation:** Generate formal API documentation (e.g., using Swagger/OpenAPI).
* **Frontend Integration:** Connect this backend to the user interface.

