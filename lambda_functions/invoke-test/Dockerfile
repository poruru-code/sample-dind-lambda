FROM public.ecr.aws/lambda/python:3.12

# Install requests
RUN pip install requests

# 透過的ロギング用パッチ
COPY lambda_functions/LayerLib/lambda_lib/python/sitecustomize.py /var/lang/lib/python3.12/site-packages/

# Copy function code
COPY lambda_functions/invoke-test/lambda_function.py ${LAMBDA_TASK_ROOT}/

CMD [ "lambda_function.lambda_handler" ]
