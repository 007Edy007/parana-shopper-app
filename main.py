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
            print("Option 2 – Add Item to Basket (coming soon)")
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
