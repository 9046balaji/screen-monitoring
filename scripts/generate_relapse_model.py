import json
import os
import pickle

class MockModel:
    def __init__(self):
        self.type = "random_forest_mock"
        self.feature_importances = {"Late night (pm)": 0.4, "Recent negative mood": 0.35, "Long unused focus mode": 0.25}
    def predict(self, features):
        return 0.85

def train_mock_model():
    """
    Creates a mock model for the hackathon. 
    In reality, we would load data/usage_log.json, 
    parse times, features, train an XGBoost/RandomForest model,
    and save it using pickle.
    """
    models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
    os.makedirs(models_dir, exist_ok=True)
    
    with open(os.path.join(models_dir, 'relapse_model.pkl'), 'wb') as f:
        pickle.dump(MockModel(), f)
        
    print("Mock relapse model saved to models/relapse_model.pkl")

if __name__ == "__main__":
    train_mock_model()
