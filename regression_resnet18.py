# -*- coding: utf-8 -*-
"""Regression_Resnet18.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/16TzLOEIfQSSPiYi0WzufYIEC1KfEXuDp
"""

# Commented out IPython magic to ensure Python compatibility.
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from PIL import Image
import torch
import torchvision
from torchvision import transforms
import torch.nn as nn
import torch.optim as optim
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

# Step 1: Setting up the environment

# Mount Google Drive
from google.colab import drive
drive.mount('/content/drive')

# Navigate to dataset folder
# %cd "/content/drive/My Drive/Liang/XPAge01_RGB/XP"

# Step 2: Loading the dataset

# Load the training and testing data from the CSV files
data = pd.read_csv('/content/drive/My Drive/Liang/XPAge01_RGB/XP/trainingdata.csv')

# Split the data into training, validation, and test sets
train_data, val_test_data = train_test_split(data, test_size=0.2, random_state=42)
val_data, test_data_df = train_test_split(val_test_data, test_size=0.5, random_state=42)

# Define the transformations to apply during training
train_transforms = transforms.Compose([
    transforms.RandomHorizontalFlip(p=0.5),
    transforms.RandomRotation(degrees=30),
    transforms.RandomResizedCrop(size=(1024, 1024), scale=(0.8, 1.0)),
    transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2, hue=0.1),
    transforms.ToTensor()
])

val_test_transforms = transforms.Compose([
    transforms.Resize((1024, 1024)),
    transforms.ToTensor()
])

# Load the images from the "JPGs" folder
train_images, val_images, test_images = [], [], []

train_data = train_data.reset_index(drop=True)
for file in train_data['filenames']:
    img = Image.open('JPGs/' + file).convert('RGB')
    img = train_transforms(img)
    train_images.append(img)

val_data = val_data.reset_index(drop=True)
for file in val_data['filenames']:
    img = Image.open('JPGs/' + file).convert('RGB')
    img = val_test_transforms(img)
    val_images.append(img)

test_data_df = test_data_df.reset_index(drop=True)
for file in test_data_df['filenames']:
    img = Image.open('JPGs/' + file).convert('RGB')
    img = val_test_transforms(img)
    test_images.append(img)

# Convert the lists of images to tensors
train_images = torch.stack(train_images)
val_images = torch.stack(val_images)
test_images = torch.stack(test_images)

# Create tensors for the labels
train_labels = torch.tensor(train_data['age'].values)
val_labels = torch.tensor(val_data['age'].values)
test_labels = torch.tensor(test_data_df['age'].values)

# Step 3: Defining the Resnet-18 model

# Load the Resnet-18 model from torchvision
resnet18 = torchvision.models.resnet18(pretrained=True)

# Modify the last layer of the model to output a single value for age estimation
num_ftrs = resnet18.fc.in_features
resnet18.fc = nn.Linear(num_ftrs, 1)

# Define the loss function and optimizer
criterion = nn.MSELoss()
optimizer = optim.Adam(resnet18.parameters(), lr=0.001)

# Set the device to GPU if available
device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# Transfer the model and data to the device
resnet18.to(device)
train_images = train_images.to(device)
train_labels = train_labels.to(device)
val_images = val_images.to(device)
val_labels = val_labels.to(device)
test_images = test_images.to(device)
test_labels = test_labels.to(device)

batch_size = 8

# Train the model
train_losses = []
val_losses = []
test_losses = []

num_batches = len(train_data) // batch_size

# Add a learning rate scheduler
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, 'min', patience=3, verbose=True)

# Set up early stopping
early_stopping = 10
best_val_loss = float('inf')
stop_counter = 0

for epoch in range(50):
    running_loss = 0.0
    for i in range(num_batches):
        # Get a batch of data
        batch_images = train_images[i * batch_size:(i + 1) * batch_size]
        batch_labels = train_labels[i * batch_size:(i + 1) * batch_size]

        # Transfer the batch to the device
        batch_images = batch_images.to(device)
        batch_labels = batch_labels.to(device)

        optimizer.zero_grad()
        outputs = resnet18(batch_images)
        loss = criterion(outputs, batch_labels.unsqueeze(1).float())
        loss.backward()
        optimizer.step()
        running_loss += loss.item()

    train_loss = running_loss / num_batches
    train_losses.append(train_loss)

    # Calculate validation loss
    with torch.no_grad():
        val_outputs = resnet18(val_images)
        val_loss = criterion(val_outputs, val_labels.unsqueeze(1).float()).item()
        val_losses.append(val_loss)

    # Update the learning rate scheduler
    scheduler.step(val_loss)

    # Implement early stopping
    if val_loss < best_val_loss:
        best_val_loss = val_loss
        stop_counter = 0
    else:
        stop_counter += 1
        if stop_counter >= early_stopping:
            break

    print(f"Epoch {epoch + 1} - Training Loss: {train_loss:.4f} - Validation Loss: {val_loss:.4f}")

# Step 5: Evaluating the model

# Create a DataLoader for the test set
test_set = torch.utils.data.TensorDataset(test_images, test_labels)
test_loader = torch.utils.data.DataLoader(test_set, batch_size=8)

# Convert the model's predictions to a numpy array and calculate the evaluation metrics
with torch.no_grad():
    # Predict the ages of the test set images
    pred = []
    true_labels = []
    for test_images, test_labels in test_loader:
        test_images = test_images.to(device)
        test_labels = test_labels.to(device)
        outputs = resnet18(test_images)
        pred.append(outputs.cpu().numpy())
        true_labels.append(test_labels.cpu().numpy())

    pred = np.concatenate(pred).flatten()
    true_labels = np.concatenate(true_labels)

    # Calculate the evaluation metrics
    r2 = r2_score(true_labels, pred)
    mse = mean_squared_error(true_labels, pred)
    rmse = np.sqrt(mse)
    mae = mean_absolute_error(true_labels, pred)

# Print the evaluation metrics
print(f"R^2 Score: {r2:.4f}")
print(f"MSE: {mse:.4f}")
print(f"RMSE: {rmse:.4f}")
print(f"MAE: {mae:.4f}")

# Add the display_images function here
def display_images(indices, title):
    fig, axes = plt.subplots(1, len(indices), figsize=(5 * len(indices), 5))
    fig.suptitle(title)
    
    for i, index in enumerate(indices):
        file = test_data_df.loc[index, 'filenames']
        img = Image.open('JPGs/' + file).convert('RGB')
        img_id = file.split('.')[0]  # Assuming the image ID is the filename without the extension
        if len(indices) > 1:
            axes[i].imshow(img)
            axes[i].set_title(f"ID: {img_id}\nIndex: {index}\nError: {errors[index]:.4f}")
            axes[i].axis('off')
        else:
            axes.imshow(img)
            axes.set_title(f"ID: {img_id}\nIndex: {index}\nError: {errors[index]:.4f}")
            axes.axis('off')
    plt.show()


# Calculate prediction errors
errors = np.abs(true_labels - pred)

# Find indices of correct predictions
correct_pred_indices = np.where(errors < 1)[0]

# Find indices of large errors (>= 2 years)
large_error_indices = np.where(errors >= 2)[0]

# Find the index of the X-ray with the maximal prediction error
max_error_index = np.argmax(errors)
max_error_value = errors[max_error_index]
print(f"Maximal prediction error: {max_error_value:.4f}")


# Display X-rays with correct predictions
display_images(correct_pred_indices, 'Correct Predictions')

# Display X-rays with errors of >= 2 years
display_images(large_error_indices, 'Large Errors (>= 2 years)')

# Display the X-ray with the maximal prediction error
display_images([max_error_index], 'Maximal Prediction Error')