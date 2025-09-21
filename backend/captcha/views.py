from rest_framework.request import Request
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from captcha.generator import CaptchaGenerator
from captcha.services import CaptchaService
import uuid
from PIL import Image
from .throttles import CaptchaRateThrottle

class CaptchaGenerateView(APIView):
    """
        Generate new captcha
    """
    permission_classes = [AllowAny]
    throttle_classes = [CaptchaRateThrottle]
    
    def get(self, request : Request) -> Response:
        try:
            generator = CaptchaGenerator()
            text : str = generator.generate_text() #This is right answer and also text in the picture
            image : Image = generator.generate_image(text)
            image_data : str = generator.image_to_base64(image) #as base64
            
            # Generate key and store in Redis
            captcha_key = CaptchaService.generate_key()
            
            #Store Correct Response For This Key
            if not CaptchaService.store_captcha_data(
                key=captcha_key,
                response=text
            ):
                return Response(
                    {"detail": "خطا در ایجاد کپچا"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            return Response({
                'key': captcha_key,
                'image_data': f"data:image/png;base64,{image_data}",
                'expires_in': CaptchaService.DEFAULT_EXPIRY
            })
            
        except Exception as e:
            print(e)
            return Response(
                {"detail": "خطا در ایجاد کپچا"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
class CaptchaRefreshView(APIView):
    """
        Invoke the old captch 
        Generate New Captcha
    """
    permission_classes = [AllowAny]
    throttle_classes = [CaptchaRateThrottle]

    def get(self , request:Request) -> Response :
        # Get the old captcha uuid from params
        old_captcha = request.query_params.get('old_captcha' , None)

        if not old_captcha:
            return Response({"detail":"آیدی کپچا قبلی وارد نشده است"} , status=status.HTTP_400_BAD_REQUEST)
        
        try:
            uuid.UUID(old_captcha)
        except ValueError:
            return Response({"detail": "فرمت آیدی کپچا نامعتبر است"}, status=status.HTTP_400_BAD_REQUEST)
        
        #Fetch the old captcha data and invoke it
        old_captcha_data = CaptchaService.fetch_captcha_data(key = old_captcha)
        if not old_captcha_data or old_captcha_data['is_used'] == True:
            return Response(
                {"detail":"کپچا قبلی معتبر نیست"},
                status=status.HTTP_400_BAD_REQUEST
            )        

        #Generate The New Captcha
        try:
            generator = CaptchaGenerator()
            text : str = generator.generate_text() #This is right answer and also text in the picture
            image : Image = generator.generate_image(text)
            image_data : str = generator.image_to_base64(image) #as base64
            
            # Generate key and store in Redis
            captcha_key = CaptchaService.generate_key()
            
            #Store Correct Response For This Key
            if not CaptchaService.store_captcha_data(
                key=captcha_key,
                response=text
            ):
                return Response(
                    {"detail": "خطا در ایجاد کپچا"}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
            # Only mark old captcha as used AFTER new one is successfully created
            old_captcha_invoke_result = CaptchaService.mark_as_used(key = old_captcha)
            
            return Response({
                'key': captcha_key,
                'image_data': f"data:image/png;base64,{image_data}",
                'expires_in': CaptchaService.DEFAULT_EXPIRY
            })
            
        except Exception as e:
            print(e)
            return Response(
                {"detail": "خطا در ایجاد کپچا"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )