FROM minio/minio:RELEASE.2024-01-25T01-54-28Z
CMD ["server", "/data", "--console-address", ":9001"]
