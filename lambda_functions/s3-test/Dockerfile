FROM public.ecr.aws/lambda/python:3.12

# インフラ・ライブラリのセットアップ (Layer / Patch)
COPY lambda_functions/LayerLib/lambda_lib/python/ /opt/python/
COPY lambda_functions/LayerLib/lambda_lib/python/sitecustomize.py /var/lang/lib/python3.12/site-packages/

# Lambda関数のコードをコピー
COPY lambda_functions/s3-test/lambda_function.py ${LAMBDA_TASK_ROOT}/

# PYTHONPATHにLayerのパスを追加
ENV PYTHONPATH="${PYTHONPATH}:/opt/python"

CMD [ "lambda_function.lambda_handler" ]
