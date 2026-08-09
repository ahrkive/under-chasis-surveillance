"""
Incremental Training Pipeline
===============================
Weekly fine-tuning of MobileNetV3-Small using newly accumulated approved images.

Strategy:
- Freeze all layers except the last 3 InvertedResidual blocks + classifier head
- Train on the FULL approved dataset (not just delta) to mitigate catastrophic forgetting
- Validate on a 20% holdout split
- Promote new model only if accuracy >= previous version
"""

import io
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader, random_split
from torchvision import transforms, models
from PIL import Image
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.database import get_session_factory
from app.inspections.models import Inspection, ModelVersion, TrainingLog
from app.inference.service import get_inference_service, LABELS

logger = logging.getLogger(__name__)


class ApprovedImageDataset(Dataset):
    """PyTorch Dataset that loads approved inspection images."""

    def __init__(self, image_paths: list[str], transform=None):
        self.image_paths = image_paths
        self.transform = transform
        # All approved images are labeled as class 0 ("ok")
        # This is a one-class learning setup initially
        self.labels = [0] * len(image_paths)

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, idx):
        img_path = self.image_paths[idx]
        try:
            image = Image.open(img_path).convert("RGB")
        except Exception:
            # Return a blank image if file is corrupted
            image = Image.new("RGB", (224, 224), (128, 128, 128))

        if self.transform:
            image = self.transform(image)

        return image, self.labels[idx]


class TrainingPipeline:
    """Orchestrates the weekly incremental training process."""

    def __init__(self):
        self.settings = get_settings()
        self.train_transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.RandomHorizontalFlip(),
            transforms.RandomVerticalFlip(),
            transforms.RandomRotation(15),
            transforms.ColorJitter(brightness=0.3, contrast=0.3),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])
        self.val_transform = transforms.Compose([
            transforms.Resize((256, 256)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])

    async def run_training(self) -> Optional[int]:
        """
        Execute the full training pipeline.

        Returns:
            New model version number if successful, None if skipped/failed.
        """
        session_factory = get_session_factory()

        async with session_factory() as db:
            # Step 1: Collect all approved image paths
            result = await db.execute(
                select(Inspection.image_local_path, Inspection.image_cloud_url)
                .where(Inspection.decision == "approved")
                .where(Inspection.image_local_path.isnot(None))
            )
            rows = result.all()
            image_paths = [row[0] for row in rows if row[0] and os.path.exists(row[0])]

            total_count = len(image_paths)
            logger.info("Training pipeline: found %d approved images.", total_count)

            # Step 2: Check minimum threshold
            # Get count from last training
            last_model = await db.execute(
                select(ModelVersion)
                .where(ModelVersion.status.in_(["active", "archived"]))
                .order_by(ModelVersion.version.desc())
                .limit(1)
            )
            last = last_model.scalar_one_or_none()
            last_count = last.training_image_count if last else 0
            new_images = total_count - last_count

            if new_images < self.settings.min_images_for_training:
                logger.info(
                    "Only %d new images (need %d). Skipping training.",
                    new_images, self.settings.min_images_for_training,
                )
                return None

            # Step 3: Determine new version number
            version_result = await db.execute(
                select(func.coalesce(func.max(ModelVersion.version), 0))
            )
            current_max = version_result.scalar()
            new_version = current_max + 1

            # Step 4: Create model version record
            model_version = ModelVersion(
                version=new_version,
                file_path=f"{self.settings.model_dir}/v{new_version:03d}_mobilenetv3.pth",
                training_image_count=total_count,
                status="training",
            )
            db.add(model_version)

            # Step 5: Create training log
            training_log = TrainingLog(
                model_version=new_version,
                new_images_count=new_images,
                total_images_count=total_count,
                status="running",
                started_at=datetime.utcnow(),
            )
            db.add(training_log)
            await db.commit()

        # Step 6: Run training (CPU/GPU bound — runs in executor)
        try:
            accuracy, loss = await self._train_model(
                image_paths=image_paths,
                new_version=new_version,
            )

            async with session_factory() as db:
                # Update model version
                result = await db.execute(
                    select(ModelVersion).where(ModelVersion.version == new_version)
                )
                model_version = result.scalar_one()
                model_version.validation_accuracy = accuracy
                model_version.trained_at = datetime.utcnow()

                # Check if new model is better than current active
                active_result = await db.execute(
                    select(ModelVersion).where(ModelVersion.status == "active")
                )
                active_model = active_result.scalar_one_or_none()
                prev_accuracy = active_model.validation_accuracy if active_model else 0.0

                if accuracy >= (prev_accuracy or 0.0):
                    # Promote new model
                    if active_model:
                        active_model.status = "archived"
                    model_version.status = "active"
                    logger.info(
                        "Model v%d promoted to active (accuracy: %.2f%% → %.2f%%)",
                        new_version, (prev_accuracy or 0) * 100, accuracy * 100,
                    )

                    # Hot-swap inference model
                    inference = get_inference_service()
                    await inference.hot_swap(new_version)
                else:
                    model_version.status = "archived"
                    logger.warning(
                        "Model v%d accuracy (%.2f%%) < previous (%.2f%%). Keeping current model.",
                        new_version, accuracy * 100, (prev_accuracy or 0) * 100,
                    )

                # Update training log
                log_result = await db.execute(
                    select(TrainingLog)
                    .where(TrainingLog.model_version == new_version)
                    .order_by(TrainingLog.started_at.desc())
                    .limit(1)
                )
                training_log = log_result.scalar_one()
                training_log.accuracy = accuracy
                training_log.loss = loss
                training_log.status = "success"
                training_log.completed_at = datetime.utcnow()

                await db.commit()

            return new_version

        except Exception as e:
            logger.error("Training failed: %s", e, exc_info=True)

            async with session_factory() as db:
                result = await db.execute(
                    select(ModelVersion).where(ModelVersion.version == new_version)
                )
                model_version = result.scalar_one()
                model_version.status = "archived"

                log_result = await db.execute(
                    select(TrainingLog)
                    .where(TrainingLog.model_version == new_version)
                    .order_by(TrainingLog.started_at.desc())
                    .limit(1)
                )
                training_log = log_result.scalar_one()
                training_log.status = "failed"
                training_log.log_output = str(e)
                training_log.completed_at = datetime.utcnow()

                await db.commit()

            return None

    async def _train_model(
        self,
        image_paths: list[str],
        new_version: int,
        epochs: int = 15,
        lr: float = 1e-4,
        batch_size: int = 16,
    ) -> tuple[float, float]:
        """
        Fine-tune MobileNetV3-Small on the approved image dataset.

        Returns:
            Tuple of (validation_accuracy, final_loss)
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self._train_sync, image_paths, new_version, epochs, lr, batch_size
        )

    def _train_sync(
        self,
        image_paths: list[str],
        new_version: int,
        epochs: int,
        lr: float,
        batch_size: int,
    ) -> tuple[float, float]:
        """Synchronous training logic (runs in thread executor)."""
        device = torch.device(self.settings.inference_device)

        # 80/20 train/val split
        indices = torch.randperm(len(image_paths)).tolist()
        val_size = max(1, int(len(image_paths) * 0.2))
        train_indices = indices[val_size:]
        val_indices = indices[:val_size]

        train_dataset = ApprovedImageDataset(
            [image_paths[i] for i in train_indices],
            transform=self.train_transform,
        )
        val_dataset = ApprovedImageDataset(
            [image_paths[i] for i in val_indices],
            transform=self.val_transform,
        )

        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True, num_workers=0)
        val_loader = DataLoader(val_dataset, batch_size=batch_size, shuffle=False, num_workers=0)

        # Build ResNet50 model matching version2.ipynb Kaggle notebook
        model = models.resnet50(weights=models.ResNet50_Weights.DEFAULT)
        model.fc = nn.Linear(model.fc.in_features, len(LABELS))

        # Try loading current model weights
        current_model_path = None
        for v in range(new_version - 1, 0, -1):
            path = f"{self.settings.model_dir}/v{v:03d}_mobilenetv3.pth"
            if os.path.exists(path):
                current_model_path = path
                break

        if current_model_path:
            try:
                state_dict = torch.load(current_model_path, map_location=device, weights_only=True)
                model.load_state_dict(state_dict)
                logger.info("Loaded previous model weights from %s", current_model_path)
            except Exception as e:
                logger.warning("Could not load previous weights: %s. Using ResNet50 pretrained.", e)

        model.to(device)

        # Freeze early layers, fine-tune layer4 + fc
        frozen_count = 0
        total_params = 0
        for name, param in model.named_parameters():
            total_params += 1
            if "fc" in name or "layer4" in name:
                param.requires_grad = True
            else:
                param.requires_grad = False
                frozen_count += 1

        logger.info("Frozen %d / %d parameters.", frozen_count, total_params)

        # Optimizer + scheduler
        optimizer = optim.AdamW(
            filter(lambda p: p.requires_grad, model.parameters()),
            lr=lr, weight_decay=1e-4,
        )
        scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.CrossEntropyLoss()

        # Training loop
        best_accuracy = 0.0
        patience = 3
        patience_counter = 0
        final_loss = 0.0

        for epoch in range(epochs):
            # Train
            model.train()
            running_loss = 0.0
            for images, labels in train_loader:
                images, labels = images.to(device), labels.to(device)
                optimizer.zero_grad()
                outputs = model(images)
                loss = criterion(outputs, labels)
                loss.backward()
                optimizer.step()
                running_loss += loss.item()

            avg_loss = running_loss / max(len(train_loader), 1)
            scheduler.step()

            # Validate
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for images, labels in val_loader:
                    images, labels = images.to(device), labels.to(device)
                    outputs = model(images)
                    _, predicted = torch.max(outputs, 1)
                    total += labels.size(0)
                    correct += (predicted == labels).sum().item()

            accuracy = correct / max(total, 1)
            final_loss = avg_loss

            logger.info(
                "Epoch %d/%d — loss: %.4f, val_accuracy: %.2f%%",
                epoch + 1, epochs, avg_loss, accuracy * 100,
            )

            # Early stopping
            if accuracy > best_accuracy:
                best_accuracy = accuracy
                patience_counter = 0
            else:
                patience_counter += 1
                if patience_counter >= patience:
                    logger.info("Early stopping at epoch %d.", epoch + 1)
                    break

        # Save model
        save_path = f"{self.settings.model_dir}/v{new_version:03d}_mobilenetv3.pth"
        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        torch.save(model.state_dict(), save_path)
        logger.info("Model saved: %s (accuracy: %.2f%%)", save_path, best_accuracy * 100)

        return best_accuracy, final_loss


# ── Singleton ────────────────────────────────────────────────────────────
_pipeline: Optional[TrainingPipeline] = None


def get_training_pipeline() -> TrainingPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = TrainingPipeline()
    return _pipeline
