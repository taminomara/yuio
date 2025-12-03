import yuio.io
import yuio.secret

if __name__ == "__main__":
    password = yuio.io.ask[yuio.secret.SecretString]("Enter nuclear launch code:")
    if password.data == "000000":
        yuio.io.success("Successfully started ITER!")
    else:
        yuio.io.error("Wrong password =(")
