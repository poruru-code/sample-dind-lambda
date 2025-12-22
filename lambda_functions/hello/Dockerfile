FROM public.ecr.aws/lambda/python:3.12

# 透過的ロギング用パッチ
COPY lambda_functions/LayerLib/lambda_lib/python/sitecustomize.py /var/lang/lib/python3.12/site-packages/

# Lambda関数のコードをコピー
COPY lambda_functions/hello/lambda_function.py ${LAMBDA_TASK_ROOT}/

# Lambda Runtime Interface Emulator (RIE) はベースイメージに含まれている
# コンテナ起動時にRIEが自動的にlambda_handlerを呼び出す

CMD [ "lambda_function.lambda_handler" ]
