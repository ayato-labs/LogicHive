import subprocess
import sys
import os

def run_command(command, check=True):
    print(f"[EXEC] {' '.join(command)}")
    result = subprocess.run(command, capture_output=True, text=True, shell=True)
    if check and result.returncode != 0:
        print(f"[ERROR] {result.stderr}")
        return False
    return True

def deploy_to_cloud_run(service_name, dockerfile_path, project_id):
    print(f"\n--- Deploying {service_name} ---")
    
    # 1. Build and Push to Artifact Registry/GCR
    image_tag = f"gcr.io/{project_id}/{service_name}"
    print(f"[INFO] Building & Pushing image: {image_tag}...")
    
    build_cmd = f"gcloud builds submit --tag {image_tag} -f {dockerfile_path} ."
    if not run_command(build_cmd):
        return False
        
    # 2. Deploy to Cloud Run
    print(f"[INFO] Deploying to Cloud Run...")
    deploy_cmd = (
        f"gcloud run deploy {service_name} "
        f"--image {image_tag} "
        f"--platform managed "
        f"--region us-central1 "
        f"--allow-unauthenticated"
    )
    if not run_command(deploy_cmd):
        return False
        
    print(f"[SUCCESS] {service_name} is now live!")
    return True

def main():
    print("=== LogicHive Cloud CI/CD (GCP) ===")
    
    project_id = input("Enter GCP Project ID: ").strip()
    if not project_id:
        print("[ERROR] Project ID is required.")
        sys.exit(1)
        
    print("\n[Selection]")
    print("[1] Deploy Business Portal (Marketing/Billing)")
    print("[2] Deploy Backend Hub (Logic Engine)")
    print("[3] Deploy Both")
    
    choice = input("Choice: ").strip()
    
    success = True
    if choice in ["1", "3"]:
        success &= deploy_to_cloud_run(
            "logichive-portal", 
            "LogicHive-Hub-Private/backend/hub/Dockerfile.portal", 
            project_id
        )
        
    if choice in ["2", "3"]:
        # Note: Hub might need its own Dockerfile if not already defined
        # For now, we use the same root but a different Dockerfile if available
        success &= deploy_to_cloud_run(
            "logichive-hub", 
            "LogicHive-Hub-Private/backend/hub/Dockerfile", # Assuming this exists or using a default
            project_id
        )
        
    if success:
        print("\n[FINAL SUCCESS] Cloud deployment completed.")
    else:
        print("\n[FAILED] One or more deployments failed.")
        sys.exit(1)

if __name__ == "__main__":
    main()
