# d3ploy

Easily deploy to S3 with multiple environment support. Version 3 supports Python 3.6+.

## Installation & Usage

To install, run `pip install d3ploy`.
To use, run `d3ploy`. Additional arguments may be specified. Run `d3ploy --help` for more information.

## Authentication

Your AWS credentials can be set in a number of ways:

1. In a ".boto" file in your home folder. See [Boto's documentation](http://docs.pythonboto.org/en/latest/boto_config_tut.html) for how to create this file.
2. In a ".aws" file in the folder you're running `d3ploy` in. Follows the same format as ".boto".
3. In the environment variables "AWS_ACCESS_KEY_ID" and "AWS_SECRET_ACCESS_KEY".

## Configuration options

When you run `d3ploy`, it will look in the current directory for a ".d3ploy.json" file that defines the different deploy enviroments and their options. At a minimum, a "default" environment is required and is the environment used if you pass no arguments to `d3ploy`. Additionally, you may pass in a different path for you config file with the `-c` or `--config` options.

To supress all output, pass `-q` or `--quiet` to the command. Note that there is not a way to set the quiet option in the config file(s).

To set the number of separate processes to use, pass `-p 10` or `--processess 10` where '10' is the number to use. If you do not want to use multiple processes, set this to '0'.

You can add as many environments as needed. Deploy to an environment by passing in its key like `d3ploy staging`. As of version 3.0, environments no longer inherit settings from the default environment. Instead, a separate `defaults` object in the config file can be used to set options across all environments.

The only required option for any environment is "bucket_name" for the S3 bucket to upload to. Additionally, you may define:

- "local_path" to upload only the contents of a directory under the current one; defaults to "." (current directory)
- "bucket_path" to upload to a subfolder in the bucket; defaults to "/" (root)
- "exclude" to specify patterns to not upload
- "acl" to specify the canned ACL set on each object. See https://docs.aws.amazon.com/AmazonS3/latest/dev/acl-overview.html#canned-acl.
- "delete" to remove files on S3 that are not present in the local directory
- "charset" to set the charset flag on 'Content-Type' headers of text files
- "caches" to set the Cache-Control header for various mimetypes. See below for more.
- "gitignore" to add all entries in a .gitignore file to the exclude patterns
- "cloudfront_id" to invalidate all paths in the given CloudFront distribution IDs. Can be a string for one distribution or an array for multiple.

### Example .d3ploy.json

```json
{
  "environments": {
    "default": {
      "bucket_name": "d3ploy-tests",
      "local_path": "./tests/files",
      "bucket_path": "/default/"
    },
    "staging": {
      "bucket_name": "d3ploy-tests",
      "local_path": "./tests/files",
      "bucket_path": "/staging/"
    }
  },
  "defaults": {
    "caches": {
      "text/css": 2592000,
      "application/javascript": 2592000,
      "image/png": 22896000,
      "image/jpeg": 22896000,
      "image/webp": 22896000,
      "image/gif": 22896000
    }
  }
}
```

## Cache-Control Headers

If you want to set Cache-Control headers on various files, add a `caches` object to your config file like:

```
"caches": {
  "text/css": 2592000,
  "application/javascript": 2592000,
  "image/png": 22896000,
  "image/jpeg": 22896000,
  "image/webp": 22896000,
  "image/gif": 22896000
}
```

Each key is the mimetype of the kind of file you want to have cached, with a value that is the seconds the `max-age` flag set to. In the above example, CSS and JavaScript files will be cached for 30 days while images will be cached for 1 year. For more about Cache-Control, read [Leverage Browser Caching](https://developers.google.com/speed/docs/insights/LeverageBrowserCaching).

## OS X Notification Center

d3ploy will attempt to alert you via Notification Center when it is completed. To enable this feature, you need pyobjc; run `pip install pyobjc` to install.

## Progress Bar

d3ploy will use the `progressbar2` module if it's available to display output. This includes a percentage completed and an ETA. To enable, run `pip install progressbar2`.

## Caution About Using the gzip Option

Almost all modern browsers will support files that are served with gzip compression. The notable exception is non-smartphone mobile browsers. If you have significant traffic over those browsers, it is advisable to avoid the gzip option. Additionally, your CDN make offer compression on-the-fly for you; this is the preferred method when available.
