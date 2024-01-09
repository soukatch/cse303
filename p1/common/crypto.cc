#include <iostream>
#include <openssl/err.h>
#include <openssl/rand.h>
#include <string>
#include <sys/stat.h>
#include <vector>

#include "contextmanager.h"
#include "crypto.h"
#include "err.h"

using namespace std;

/// Load an RSA public key from the given filename
///
/// @param filename The name of the file that has the public key in it
///
/// @return An RSA context for encrypting with the provided public key, or
///         nullptr on error
RSA *load_pub(const char *filename) {
  FILE *pub = fopen(filename, "r");
  if (pub == nullptr)
    return err<RSA *>(nullptr, "Error opening public key file");
  ContextManager cf([&]() { fclose(pub); });
  RSA *rsa = PEM_read_RSAPublicKey(pub, 0, 0, 0);
  if (rsa == nullptr)
    return err<RSA *>(nullptr, "Error reading public key file");
  return rsa;
}

/// Load an RSA private key from the given filename
///
/// @param filename The name of the file that has the private key in it
///
/// @return An RSA context for encrypting with the provided private key, or
///         nullptr on error
RSA *load_pri(const char *filename) {
  FILE *pri = fopen(filename, "r");
  if (pri == nullptr)
    return err<RSA *>(nullptr, "Error opening private key file");
  ContextManager cf([&]() { fclose(pri); });
  RSA *rsa = PEM_read_RSAPrivateKey(pri, 0, 0, 0);
  if (rsa == nullptr)
    return err<RSA *>(nullptr, "Error reading public key file");
  return rsa;
}

/// Produce an RSA key and save its public and private parts to files
///
/// @param pub The name of the public key file to generate
/// @param pri The name of the private key file to generate
///
/// @return true on success, false on any error
bool generate_rsa_key_files(const string &pub, const string &pri) {
  cout << "Generating RSA keys as (" << pub << ", " << pri << ")\n";
  // When we create a new RSA keypair, we need to know the #bits (see constant
  // above) and the desired exponent to use in the public key.  The exponent
  // needs to be a bignum.  We'll use the RSA_F4 default value:
  BIGNUM *bn = BN_new();
  if (bn == nullptr)
    return err(false, "Error in BN_new()");
  ContextManager bnfree([&]() { BN_free(bn); }); // ensure bn gets freed

  if (BN_set_word(bn, RSA_F4) != 1)
    return err(false, "Error in BN_set_word()");

  // Now we can create the key pair
  RSA *rsa = RSA_new();
  if (rsa == nullptr)
    return err(false, "Error in RSA_new()");
  ContextManager rsafree([&]() { RSA_free(rsa); }); // ensure rsa gets freed

  if (RSA_generate_key_ex(rsa, RSA_KEYSIZE, bn, nullptr) != 1)
    return err(false, "Error in RSA_genreate_key_ex()");

  // Create/truncate the files
  FILE *pubfile = fopen(pub.c_str(), "w");
  if (pubfile == nullptr)
    return err(false, "Error opening public key file for output");
  ContextManager pubclose([&]() { fclose(pubfile); }); // ensure pub gets closed

  FILE *prifile = fopen(pri.c_str(), "w");
  if (prifile == nullptr)
    return err(false, "Error opening private key file for output");
  ContextManager priclose([&]() { fclose(prifile); }); // ensure pub gets closed

  // Perform the writes
  if (PEM_write_RSAPublicKey(pubfile, rsa) != 1)
    return err(false, "Error writing public key");
  else if (PEM_write_RSAPrivateKey(prifile, rsa, 0, 0, 0, 0, 0) != 1)
    return err(false, "Error writing private key");
  return true;
}

/// Run the AES symmetric encryption/decryption algorithm on a buffer of bytes.
/// Note that this will do either encryption or decryption, depending on how the
/// provided CTX has been configured.  After calling, the CTX cannot be used
/// again until it is reset.
///
/// NB: This is a forward declaration.  This version of aes_crypt_msg is
///     implemented in my_crypto.cc.
///
/// @param ctx The pre-configured AES context to use for this operation
/// @param msg A buffer of bytes to encrypt/decrypt
///
/// @return A vector with the encrypted or decrypted result, or an empty
///         vector if there was an error
vector<uint8_t> aes_crypt_msg(EVP_CIPHER_CTX *ctx, const unsigned char *start,
                              int count);

/// Run the AES symmetric encryption/decryption algorithm on a vector.  Note
/// that this will do either encryption or decryption, depending on how the
/// provided CTX has been configured.  After calling, the CTX cannot be used
/// again until it is reset.
///
/// @param ctx The pre-configured AES context to use for this operation
/// @param msg A vector to encrypt/decrypt
///
/// @return A vector with the encrypted or decrypted result, or an empty
///         vector if there was an error
vector<uint8_t> aes_crypt_msg(EVP_CIPHER_CTX *ctx, const vector<uint8_t> &msg) {
  return aes_crypt_msg(ctx, msg.data(), msg.size());
}

/// Run the AES symmetric encryption/decryption algorithm on a string. Note that
/// this will do either encryption or decryption, depending on how the provided
/// CTX has been configured.  After calling, the CTX cannot be used again until
/// it is reset.
///
/// @param ctx The pre-configured AES context to use for this operation
/// @param msg A string to encrypt/decrypt
///
/// @return A vector with the encrypted or decrypted result, or an empty
///         vector if there was an error
vector<uint8_t> aes_crypt_msg(EVP_CIPHER_CTX *ctx, const string &msg) {
  return aes_crypt_msg(ctx, (unsigned char *)msg.c_str(), msg.length());
}

/// Create an AES key.  A key is two parts, the key itself, and the
/// initialization vector.  Each is just random bits.  Our key will be a stream
/// of random bits, long enough to be split into the actual key and the iv.
///
/// @return A vector holding the key and iv bits, or an empty vector on error
vector<uint8_t> create_aes_key() {
  vector<uint8_t> key(AES_KEYSIZE + AES_IVSIZE);
  if (!RAND_bytes(key.data(), AES_KEYSIZE) ||
      !RAND_bytes(key.data() + AES_KEYSIZE, AES_IVSIZE))
    return err<vector<uint8_t>>({}, "Error in RAND_bytes()");
  return key;
}

/// Create an aes context for doing a single encryption or decryption.  The
/// context must be reset after each full encrypt/decrypt.
///
/// @param key     A vector holding the bits of the key and iv
/// @param encrypt true to encrypt, false to decrypt
///
/// @return An AES context for doing encryption.  Note that the context can be
///         reset in order to re-use this object for another encryption.
EVP_CIPHER_CTX *create_aes_context(const vector<uint8_t> &key, bool encrypt) {
  // create and initialize a context for the AES operations we are going to do
  EVP_CIPHER_CTX *ctx = EVP_CIPHER_CTX_new();
  if (ctx == nullptr)
    return err<EVP_CIPHER_CTX *>(nullptr,
                                 "Error: OpenSSL couldn't create context: ",
                                 ERR_error_string(ERR_get_error(), 0));
  ContextManager c([&]() { EVP_CIPHER_CTX_cleanup(ctx); }); // reclaim on exit

  // Make sure the key and iv lengths we have up above are valid
  if (!EVP_CipherInit_ex(ctx, EVP_aes_256_cbc(), 0, 0, 0, encrypt))
    return err<EVP_CIPHER_CTX *>(nullptr,
                                 "Error: OpenSSL couldn't initialize context: ",
                                 ERR_error_string(ERR_get_error(), 0));
  if ((EVP_CIPHER_CTX_key_length(ctx) != AES_KEYSIZE) ||
      (EVP_CIPHER_CTX_iv_length(ctx) != AES_IVSIZE))
    return err<EVP_CIPHER_CTX *>(nullptr,
                                 "Error: OpenSSL couldn't initialize context: ",
                                 ERR_error_string(ERR_get_error(), 0));

  // Set the key and iv on the AES context, and set the mode to encrypt or
  // decrypt
  if (!EVP_CipherInit_ex(ctx, nullptr, nullptr, key.data(),
                         key.data() + AES_KEYSIZE, encrypt))
    return err<EVP_CIPHER_CTX *>(nullptr,
                                 "Error: OpenSSL couldn't re-init context: ",
                                 ERR_error_string(ERR_get_error(), 0));
  c.disable(); // don't reclaim ctx on exit, because we're good
  return ctx;
}

/// Reset an existing AES context, so that we can use it for another
/// encryption/decryption
///
/// @param ctx     The AES context to reset
/// @param key     A vector holding the bits of the key and iv.  Should be
///                generated by create_aes_key().
/// @param encrypt true to create an encryption context, false to create a
///                decryption context
///
/// @return false on error, true if the context is reset and ready to use again
bool reset_aes_context(EVP_CIPHER_CTX *ctx, vector<uint8_t> &key,
                       bool encrypt) {
  if (!EVP_CipherInit_ex(ctx, nullptr, nullptr, key.data(),
                         key.data() + AES_KEYSIZE, encrypt)) {
    EVP_CIPHER_CTX_cleanup(ctx);
    return err(false, "Error: OpenSSL couldn't re-init context: ",
               ERR_error_string(ERR_get_error(), 0));
  }
  return true;
}

/// When an AES context is done being used, call this to reclaim its memory
///
/// @param ctx The context to reclaim
void reclaim_aes_context(EVP_CIPHER_CTX *ctx) { EVP_CIPHER_CTX_free(ctx); }

/// If the given basename resolves to basename.pri and basename.pub, then load
/// basename.pri and return it.  If one or the other doesn't exist, then there's
/// an error.  If both don't exist, create them and then load basename.pri.
///
/// @param basename The basename of the .pri and .pub files for RSA
///
/// @return The RSA context from loading the private file, or nullptr on error
RSA *init_RSA(const string &basename) {
  string pubfile = basename + ".pub", prifile = basename + ".pri";

  struct stat stat_buf;
  bool pub_exists = (stat(pubfile.c_str(), &stat_buf) == 0);
  bool pri_exists = (stat(prifile.c_str(), &stat_buf) == 0);

  if (!pub_exists && !pri_exists)
    generate_rsa_key_files(pubfile, prifile);
  else if (pub_exists && !pri_exists)
    return err<RSA *>(nullptr, "Error: cannot find ", basename.c_str(), ".pri");
  else if (!pub_exists && pri_exists)
    return err<RSA *>(nullptr, "Error: cannot find ", basename.c_str(), ".pub");
  return load_pri(prifile.c_str());
}