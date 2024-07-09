# ADIK STORE

ADIK STORE is a website for selling sneakers to resellers.

## Description

ADIK STORE provides an online platform where resellers can buy and sell sneakers.

## Requirements

All the dependencies and required packages are listed in the `requirements.txt` file.

## Installation

To install and set up the project, follow these steps:

1. **Clone the repository:**
    ```bash
    git clone https://github.com/yourusername/adik_store.git
    cd adik_store
    ```

2. **Create a virtual environment:**
    ```bash
    python -m venv .venv
    ```

3. **Activate the virtual environment:**
    - On Windows:
      ```bash
      .venv\Scripts\activate
      ```
    - On macOS/Linux:
      ```bash
      source .venv/bin/activate
      ```

4. **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5. **Create a `.env` file in the root directory of your project and add the necessary environment variables:**
    ```
    EMAIL=your_email@example.com
    PASSWORD=your_password
    DATABASE_URL=your_database_url
    SECRET=your_secret_key
    API_KEY=your_api_key
    ```

6. **Run the application:**
    ```bash
    uvicorn app.main:app --reload
    ```

## Usage

ADIK STORE is an e-commerce website where users can browse and purchase sneakers. The website includes features like product listings, search functionality, user authentication, and a shopping cart.

## License

This project does not have a license.
