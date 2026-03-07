import os
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image as PILImage
from products.models import ProductImage, Product
from django.db import transaction

class ImageService:
    MAX_IMAGE_SIZE = (1200, 1200)

    @classmethod
    @transaction.atomic
    def process_and_save_product_image(cls, product: Product, image_file, is_primary: bool = False, **kwargs) -> ProductImage:
        """
        Processes image (resizes, compresses to JPEG) and saves it. 
        Enforces only one primary image per product.
        """
        if is_primary:
            # Demote existing primary images
            ProductImage.objects.filter(product=product, is_primary=True).update(is_primary=False)
            
        elif not ProductImage.objects.filter(product=product).exists():
            # If it's the first image, make it primary automatically
            is_primary = True

        # Open image with PIL
        img = PILImage.open(image_file)
        
        # Convert to RGB if necessary
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
            
        # Resize maintaining aspect ratio
        img.thumbnail(cls.MAX_IMAGE_SIZE, PILImage.Resampling.LANCZOS)
        
        # Save to BytesIO
        output = BytesIO()
        img.save(output, format='JPEG', quality=85)
        output.seek(0)
        
        # Construct new InMemoryUploadedFile
        filename = os.path.splitext(image_file.name)[0] + '.jpg'
        processed_file = InMemoryUploadedFile(
            file=output,
            field_name='image',
            name=filename,
            content_type='image/jpeg',
            size=output.tell(),
            charset=None
        )

        # Create ProductImage instance
        return ProductImage.objects.create(
            product=product,
            image=processed_file,
            is_primary=is_primary,
            **kwargs
        )
