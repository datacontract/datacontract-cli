# def add_s3_connection_dask_json(data_contract, scan, server):
#     s3_access_key_id = os.getenv('DATACONTRACT_S3_ACCESS_KEY_ID')
#     s3_secret_access_key = os.getenv('DATACONTRACT_S3_SECRET_ACCESS_KEY')
#     lines = server.delimiter == "new_line"
#     for model_name in data_contract.models:
#         logging.info(f"Connecting to {server.location}")
#         df = dd.read_json(
#             server.location,
#             lines=lines,
#             storage_options={'key': s3_access_key_id,
#                              'secret': s3_secret_access_key,
#                              'client_kwargs': {'endpoint_url': server.endpointUrl}
#                              })
#         scan.add_dask_dataframe(dataset_name=model_name, dask_df=df, data_source_name=server.type)

# def add_s3_connection_dask_csv(data_contract, scan, server):
#     s3_access_key_id = os.getenv('DATACONTRACT_S3_ACCESS_KEY_ID')
#     s3_secret_access_key = os.getenv('DATACONTRACT_S3_SECRET_ACCESS_KEY')
#     for model_name in data_contract.models:
#         logging.info(f"Connecting to {server.location}")
#         df = dd.read_csv(
#             server.location,
#             storage_options={'key': s3_access_key_id,
#                              'secret': s3_secret_access_key,
#                              'client_kwargs': {'endpoint_url': server.endpointUrl}
#                              })
#         scan.add_dask_dataframe(dataset_name=model_name, dask_df=df, data_source_name=server.type)

