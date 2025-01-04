from concurrent.futures import ThreadPoolExecutor
from email_account_creator import email_account_creator
import time

def main():
    # Number of concurrent threads to run
    num_threads = 3
    
    # Create a thread pool
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        # Submit tasks to the thread pool
        futures = []
        for i in range(num_threads):
            future = executor.submit(email_account_creator, i+1)  # Pass thread ID
            futures.append(future)
        
        # Wait for all tasks to complete and collect results
        results = []
        for future in futures:
            try:
                result = future.result()
                if result:
                    results.append(result)
            except Exception as e:
                print(f"Thread failed with error: {str(e)}")
        
        # Print summary
        print("\n=== Account Creation Summary ===")
        print(f"Total attempts: {num_threads}")
        print(f"Successful accounts: {len(results)}")
        print("\nCreated accounts:")
        for account in results:
            print(f"Email: {account['email']}, Password: {account['password']}")

if __name__ == "__main__":
    start_time = time.time()
    main()
    elapsed_time = time.time() - start_time
    print(f"\nTotal execution time: {elapsed_time:.2f} seconds") 