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

# View contents of the current basket
def view_basket(cursor, current_basket_id):
    if current_basket_id is None:
        print("\nYour basket is empty.")
        return
    # Get basket contents
    cursor.execute("""
        SELECT 
            p.product_description,
            s.seller_name,
            bc.quantity,
            bc.price,
            (bc.quantity * bc.price) AS line_total
        FROM basket_contents bc
        JOIN products p ON bc.product_id = p.product_id
        JOIN sellers s ON bc.seller_id = s.seller_id
        WHERE bc.basket_id = ?
    """, (current_basket_id,))
    items = cursor.fetchall()
    if not items:
        print("\nYour basket is empty.")
        return
    print("\nYour Current Basket:\n")
    print("{:<5} {:<50} {:<20} {:<8} {:<10} {:<10}".format(
        "No.", "Product", "Seller", "Qty", "Price", "Total"
    ))
    print("-" * 110)
    total = 0
    for i, item in enumerate(items, start=1):
        description, seller, qty, price, line_total = item
        total += line_total
        print("{:<5} {:<50} {:<20} {:<8} £{:<8.2f} £{:<8.2f}".format(
            i, description, seller, qty, price, line_total
        ))
    print("\nTotal Basket Cost: £{:.2f}".format(total))

# Change the quantity of an item in the basket
def change_item_quantity(cursor, conn, current_basket_id):
    if current_basket_id is None:
        print("\nYour basket is empty.")
        return
    # Get basket contents
    cursor.execute("""
        SELECT bc.product_id, bc.seller_id, p.product_description, s.seller_name, bc.quantity, bc.price
        FROM basket_contents bc
        JOIN products p ON bc.product_id = p.product_id
        JOIN sellers s ON bc.seller_id = s.seller_id
        WHERE bc.basket_id = ?
    """, (current_basket_id,))
    items = cursor.fetchall()
    if not items:
        print("\nYour basket is empty.")
        return
    # Display basket items
    print("\nYour Current Basket:\n")
    print("{:<5} {:<50} {:<20} {:<8} {:<10}".format("No.", "Product", "Seller", "Qty", "Price"))
    print("-" * 95)
    for i, item in enumerate(items, start=1):
        _, _, product, seller, qty, price = item
        print("{:<5} {:<50} {:<20} {:<8} £{:<.2f}".format(i, product, seller, qty, price))
    # Select item to change
    if len(items) == 1:
        selected_index = 0
    else:
        while True:
            try:
                selected_index = int(input("\nEnter the basket item no. to update: ")) - 1
                if 0 <= selected_index < len(items):
                    break
                else:
                    print("The basket item no. you have entered is invalid.")
            except ValueError:
                print("Please enter a valid number.")
    selected_item = items[selected_index]
    product_id = selected_item[0]
    seller_id = selected_item[1]
    # Prompt for new quantity
    new_quantity = 0
    while new_quantity <= 0:
        try:
            new_quantity = int(input("Enter the new quantity: "))
            if new_quantity <= 0:
                print("The quantity must be greater than 0.")
        except ValueError:
            print("Please enter a valid number.")
    # Update quantity in basket
    cursor.execute("""
        UPDATE basket_contents
        SET quantity = ?
        WHERE basket_id = ? AND product_id = ? AND seller_id = ?
    """, (new_quantity, current_basket_id, product_id, seller_id))
    conn.commit()
    # Display updated basket
    print("\nQuantity updated successfully.\n")
    view_basket(cursor, current_basket_id)

# Remove an item from the basket
def remove_item_from_basket(cursor, conn, current_basket_id):
    if current_basket_id is None:
        print("\nYour basket is empty.")
        return
    # Get basket contents
    cursor.execute("""
        SELECT bc.product_id, bc.seller_id, p.product_description, s.seller_name, bc.quantity, bc.price
        FROM basket_contents bc
        JOIN products p ON bc.product_id = p.product_id
        JOIN sellers s ON bc.seller_id = s.seller_id
        WHERE bc.basket_id = ?
    """, (current_basket_id,))
    items = cursor.fetchall()
    if not items:
        print("\nYour basket is empty.")
        return
    # Display basket
    print("\nYour Current Basket:\n")
    print("{:<5} {:<50} {:<20} {:<8} {:<10}".format("No.", "Product", "Seller", "Qty", "Price"))
    print("-" * 95)
    for i, item in enumerate(items, start=1):
        _, _, product, seller, qty, price = item
        print("{:<5} {:<50} {:<20} {:<8} £{:<.2f}".format(i, product, seller, qty, price))
    # Select item to remove
    if len(items) == 1:
        selected_index = 0
    else:
        while True:
            try:
                selected_index = int(input("\nEnter the basket item no. to remove: ")) - 1
                if 0 <= selected_index < len(items):
                    break
                else:
                    print("The basket item no. you have entered is invalid.")
            except ValueError:
                print("Please enter a valid number.")
    selected_item = items[selected_index]
    product_id = selected_item[0]
    seller_id = selected_item[1]
    # Confirm removal
    confirm = input("Are you sure you want to remove this item? (Y/N): ").strip().upper()
    if confirm != 'Y':
        print("Item not removed.")
        return
    # Remove the item
    cursor.execute("""
        DELETE FROM basket_contents
        WHERE basket_id = ? AND product_id = ? AND seller_id = ?
    """, (current_basket_id, product_id, seller_id))
    conn.commit()
    # Check if basket is now empty
    cursor.execute("""
        SELECT COUNT(*) FROM basket_contents WHERE basket_id = ?
    """, (current_basket_id,))
    count = cursor.fetchone()[0]
    if count == 0:
        print("\nYour basket is now empty.")
    else:
        print("\nItem removed. Updated basket:\n")
        view_basket(cursor, current_basket_id)
# Checkout the current basket
def checkout_basket(cursor, conn, shopper_id, current_basket_id):
    if current_basket_id is None:
        print("\nYour basket is empty.")
        return

    # Get basket contents
    cursor.execute("""
        SELECT product_id, seller_id, quantity, price
        FROM basket_contents
        WHERE basket_id = ?
    """, (current_basket_id,))
    items = cursor.fetchall()

    if not items:
        print("\nYour basket is empty.")
        return

    # Show basket first
    print("\nYour Basket for Checkout:\n")
    view_basket(cursor, current_basket_id)

    # Confirm checkout
    confirm = input("\nDo you wish to proceed with the checkout (Y or N)? ").strip().upper()
    if confirm != 'Y':
        print("Checkout cancelled.")
        return
    try:
        # Start transaction
        conn.execute('BEGIN TRANSACTION')
        # Insert into shopper_orders
        cursor.execute("""
            INSERT INTO shopper_orders (shopper_id, order_date, order_status)
            VALUES (?, DATE('now'), 'Placed')
        """, (shopper_id,))
        order_id = cursor.lastrowid
        # Insert each item into ordered_products
        for product_id, seller_id, quantity, price in items:
            cursor.execute("""
                INSERT INTO ordered_products (order_id, product_id, seller_id, quantity, price, ordered_product_status)
                VALUES (?, ?, ?, ?, ?, 'Placed')
            """, (order_id, product_id, seller_id, quantity, price))
        # Delete from basket_contents and shopper_baskets
        cursor.execute("DELETE FROM basket_contents WHERE basket_id = ?", (current_basket_id,))
        cursor.execute("DELETE FROM shopper_baskets WHERE basket_id = ?", (current_basket_id,))
        # Commit transaction
        conn.commit()
        print("\nCheckout complete, your order has been placed.")
    except Exception as e:
        conn.rollback()
        print("Something went wrong during checkout:", e)

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
            # View current basket
            view_basket(cursor, current_basket_id)
        elif choice == '4':
            # Change quantity of an item in the basket
            change_item_quantity(cursor, conn, current_basket_id)
        elif choice == '5':
            # Remove item from basket
            remove_item_from_basket(cursor, conn, current_basket_id)
        elif choice == '6':
            # Checkout current basket
            before = current_basket_id
            checkout_basket(cursor, conn, shopper_id, current_basket_id)
            # Confirm basket was emptied
            cursor.execute("""
                SELECT COUNT(*) FROM basket_contents WHERE basket_id = ?
            """, (before,))
            if cursor.fetchone()[0] == 0:
                current_basket_id = None  # Only clear if basket was emptied
        elif choice == '7':
            print("Exiting... Goodbye!")
            break
        else:
            print("Invalid choice. Please enter a number between 1 and 7.")

    close_db(conn)


if __name__ == "__main__":
    main()
