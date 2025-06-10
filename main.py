from db_connection import connect_db, close_db

def display_menu():
    print("\nPARANÁ – SHOPPER MAIN MENU")
    print("1. Display your order history")
    print("2. Add an item to your basket")
    print("3. View your basket")
    print("4. Change the quantity of an item in your basket")
    print("5. Remove an item from your basket")
    print("6. Checkout")
    print("7. Exit")


# Prompt for a valid shopper_id
def get_valid_shopper(cursor):
    shopper_id = input("Enter your Shopper ID: ")
    cursor.execute("""
        SELECT shopper_first_name, shopper_surname
        FROM shoppers
        WHERE shopper_id = ?
    """, (shopper_id,))
    result = cursor.fetchone()

    if result:
        first_name, surname = result
        print(f"\nWelcome, {first_name} {surname}!")
        return int(shopper_id)
    else:
        print("\nError: Shopper ID not found. Exiting program.")
        return None

# Check for existing basket created today for this shopper
def get_current_basket_id(cursor, shopper_id):
    cursor.execute("""
        SELECT basket_id
        FROM shopper_baskets
        WHERE shopper_id = ?
        AND DATE(basket_created_date_time) = DATE('now')
        ORDER BY basket_created_date_time DESC
        LIMIT 1
    """, (shopper_id,))
    result = cursor.fetchone()
    if result:
        return result[0]  # basket_id
    else:
        return None


# Display order history for the logged-in shopper
def view_order_history(cursor, shopper_id):
    cursor.execute("""
        SELECT 
            o.order_id,
            o.order_date,
            p.product_description,
            s.seller_name,
            op.price,
            op.quantity,
            op.ordered_product_status
        FROM shopper_orders o
        JOIN ordered_products op ON o.order_id = op.order_id
        JOIN products p ON op.product_id = p.product_id
        JOIN sellers s ON op.seller_id = s.seller_id
        WHERE o.shopper_id = ?
        ORDER BY o.order_date DESC, o.order_id;
    """, (shopper_id,))

    results = cursor.fetchall()

    if not results:
        print("\nNo orders placed by this customer.")
        return

    print("\n{:<10} {:<12} {:<50} {:<20} {:<10} {:<5} {:<10}".format(
        "OrderID", "Order Date", "Product Description", "Seller", "Price", "Qty", "Status"
    ))
    print("-" * 130)

    for row in results:
        order_id, order_date, description, seller, price, qty, status = row
        print("{:<10} {:<12} {:<50} {:<20} £{:<8.2f} {:<5} {:<10}".format(
            order_id, order_date, description, seller, price, qty, status
        ))

# Display a numbered list of options and return the selected ID
def _display_options(all_options, title, type):
    option_num = 1
    option_list = []
    print("\n", title, "\n")
    for option in all_options:
        code = option[0]
        desc = option[1]
        print("{0}.\t{1}".format(option_num, desc))
        option_num += 1
        option_list.append(code)
    selected_option = 0
    while selected_option > len(option_list) or selected_option == 0:
        prompt = "Enter the number against the " + type + " you want to choose: "
        selected_option = int(input(prompt))
    return option_list[selected_option - 1]

# Add an item to the shopper's basket – Step 1: Select category
def add_to_basket(cursor, conn, shopper_id, current_basket_id):
    # Get all categories in alphabetical order
    cursor.execute("""
        SELECT category_id, category_description
        FROM categories
        ORDER BY category_description ASC
    """)
    categories = cursor.fetchall()

    # Let the user choose a category
    category_id = _display_options(categories, "Product Categories", "category")
    # Get all available products in the selected category (alphabetical order)
    cursor.execute("""
        SELECT product_id, product_description
        FROM products
        WHERE category_id = ?
        AND product_status = 'Available'
        ORDER BY product_description ASC
    """, (category_id,))
    products = cursor.fetchall()

    if not products:
        print("No available products in this category.")
        return

    # Let the user choose a product
    product_id = _display_options(products, "Available Products", "product")
    # Get all sellers for the selected product with their prices
    cursor.execute("""
        SELECT s.seller_id, s.seller_name || ' (£' || printf('%.2f', ps.price) || ')'
        FROM product_sellers ps
        JOIN sellers s ON ps.seller_id = s.seller_id
        WHERE ps.product_id = ?
        ORDER BY s.seller_name ASC
    """, (product_id,))
    sellers = cursor.fetchall()

    if not sellers:
        print("This product is not currently sold by any seller.")
        return

    # Let the user choose a seller
    seller_id = _display_options(sellers, "Sellers and Prices", "seller")
    # Prompt user for quantity (> 0)
    quantity = 0
    while quantity <= 0:
        try:
            quantity = int(input("Enter the quantity you want to order: "))
            if quantity <= 0:
                print("The quantity must be greater than 0.")
        except ValueError:
            print("Please enter a valid number.")
    # Get the price for the selected seller and product
    cursor.execute("""
        SELECT price
        FROM product_sellers
        WHERE product_id = ? AND seller_id = ?
    """, (product_id, seller_id))
    price_result = cursor.fetchone()

    if not price_result:
        print("Error: Price not found for selected product and seller.")
        return

    price = price_result[0]

    # If no current basket, create one now
    if current_basket_id is None:
        cursor.execute("INSERT INTO shopper_baskets (shopper_id, basket_created_date_time) VALUES (?, datetime('now'))", (shopper_id,))
        current_basket_id = cursor.lastrowid

    # Insert into basket_contents
    cursor.execute("""
        INSERT INTO basket_contents (basket_id, product_id, seller_id, quantity, price)
        VALUES (?, ?, ?, ?, ?)
    """, (current_basket_id, product_id, seller_id, quantity, price))

    conn.commit()

    print("Item added to your basket.")
    return current_basket_id  # So main() can track the updated basket





def main():
    conn, cursor = connect_db()

    shopper_id = get_valid_shopper(cursor)
    # Check for today's active basket
    current_basket_id = get_current_basket_id(cursor, shopper_id)
    if current_basket_id:
        print(f"\nYou have an existing basket from today (Basket ID: {current_basket_id}).")
    else:
        print("\nNo basket found for today. One will be created when you add an item.")
    if shopper_id is None:
        close_db(conn)
        return

    while True:
        display_menu()
        choice = input("\nEnter your choice (1-7): ")

        if choice == '1':
            # Display order history
            view_order_history(cursor, shopper_id)
            print("Option 1 – Order History (coming soon)")
        elif choice == '2':
            # Add an item to the basket
            updated_basket_id = add_to_basket(cursor, conn, shopper_id, current_basket_id)
            if updated_basket_id:
                current_basket_id = updated_basket_id  # Update if a new basket was created
        elif choice == '3':
            print("Option 3 – View Basket (coming soon)")
        elif choice == '4':
            print("Option 4 – Change Item Quantity (coming soon)")
        elif choice == '5':
            print("Option 5 – Remove Item from Basket (coming soon)")
        elif choice == '6':
            print("Option 6 – Checkout (coming soon)")
        elif choice == '7':
            print("Exiting... Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 7.")

    close_db(conn)


if __name__ == "__main__":
    main()
