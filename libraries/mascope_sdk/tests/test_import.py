from importlib.metadata import version

if __name__ == "__main__":
    try:
        import mascope_sdk

        mascope_sdk_version = version("mascope_sdk")
        print(f"Mascope SDK version {mascope_sdk_version} installed :-)")
    except ImportError as e:
        print("Mascope SDK not installed :-(")
