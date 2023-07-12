# srvc-neo4j

This is a neo4j-based prototype.

## Setup

1. Navigate to the `orchestrator` directory:
    ```bash
    cd orchestrator
    ```

2. Install the required Python packages:
    ```bash
    pip install -r requirements.txt
    ```

3. Set the `FLASK_APP` environment variable. Make sure to replace `src/app` with the correct path to your 
    ```bash
    export FLASK_APP=src/app.py
    ```
    
4. Start the Flask application:
    ```bash
    flask run
    ```

5. The application should now be running at [http://localhost:5000](http://localhost:5000).
