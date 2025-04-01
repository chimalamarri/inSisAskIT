import shutil
import os
import time

def backup_model():
    # Paths to your centroids and embeddings files
    centroid_file = "category_wise_centroid.npy"
    embedding_file = "embeddings.npy"
    
    # Backup directory (create if it doesn't exist)
    backup_dir = "backup"
    os.makedirs(backup_dir, exist_ok=True)
    
    # Timestamp for backup filename
    timestamp = time.strftime('%Y%m%d%H%M%S')
    
    # Backup filenames with timestamp
    centroid_backup = f"centroid_backup_{timestamp}.npy"
    embedding_backup = f"embedding_backup_{timestamp}.npy"
    
    try:
        # Backup centroids
        shutil.copyfile(centroid_file, os.path.join(backup_dir, centroid_backup))
        print(f"Centroid backup created: {centroid_backup}")
        
        # Backup embeddings
        shutil.copyfile(embedding_file, os.path.join(backup_dir, embedding_backup))
        print(f"Embedding backup created: {embedding_backup}")
        
    except Exception as e:
        print(f"Error backing up files: {e}")

if __name__ == "__main__":
    backup_model()
