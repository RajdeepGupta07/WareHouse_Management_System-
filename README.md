Visual Warehouse Management System
A complete web-based application for managing warehouse inventory with an interactive, visual floor plan. This system provides a user-friendly interface to add, edit, and track products in specific locations, manage customer orders, and view key statistics.

Note: Replace the image URL above with a screenshot of your actual running application!

Features
Interactive Floor Plan: A visual, 2D schematic of the entire warehouse layout, showing all modules and trays.

Real-time Visualization: Occupied and empty trays are color-coded for instant status recognition.

Product Highlighting: Search for products by SKU or name, and the corresponding tray will glow and scroll into view.

Search Result Display: A dedicated panel shows the name and location of the searched product for clarity.

Inventory Management: Full CRUD (Create, Read, Update, Delete) functionality for products.

User-Friendly Location Assignment: A two-step dropdown menu allows for quick and error-free assignment of products to available trays.

Order Management: Create and manage customer orders. View order details and status (Pending, Partial, Completed).

Persistent Data Storage: The backend uses a SQLite database to ensure all inventory and order data is saved permanently.

Dashboard Analytics: A dedicated tab shows key performance indicators like Total SKUs, Items in Stock, Total Orders, and Pending Orders.

Tech Stack
This project is built with a separate frontend and backend.

Frontend:

HTML5

Tailwind CSS for styling.

Vanilla JavaScript for all client-side logic and DOM manipulation.

Backend:

Python 3

FastAPI for creating the robust, high-performance API.

SQLAlchemy as the ORM (Object-Relational Mapper) to interact with the database.

SQLite for the file-based database.

Uvicorn as the ASGI server to run the backend.
