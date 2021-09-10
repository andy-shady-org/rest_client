# rest_client

Simple example of REST API client, with checking, etc using sessions.

use:

look at __getattr__, this is where the magic lies.

no need to call 
```python
  Client.query('/my_api', 'GET', dict(name='bob'), age=50)
```
You can use like:

```python
  Client.get('/my_api', 'next_arg', name='bob', age=50)
```  

This will result in URL parse of: "https://server:port/my_api/next_arg?name=bob&age=50"

Full Example:

```python
In [1]: from rest_client import *
In [2]: client = Client('example.com', 'my-api-token', verbose=3, simulation=True)
DEBUG:root:Setting level to DEBUG
DEBUG:urllib3.util.retry:Converted retries value: 5 -> Retry(total=5, connect=None, read=None, redirect=None, status=None)
DEBUG:root:Client Load Complete, loglevel set to DEBUG

In [3]: client.get('my_endpoint')
INFO:root:Final URL: https://example.com:443/api/my_endpoint, Method: get
Out[3]: {'status_code': 200, 'data': '', 'ok': 1}

In [4]: client.get('my_endpoint', 'arg1')
INFO:root:Final URL: https://example.com:443/api/my_endpoint/arg1, Method: get
Out[4]: {'status_code': 200, 'data': '', 'ok': 1}

In [5]: client.get('my_endpoint', 'arg1', name='bob', age=50)
DEBUG:root:Query: age=50&name=bob
INFO:root:Final URL: https://example.com:443/api/my_endpoint/arg1?age=50&name=bob, Method: get
Out[5]: {'status_code': 200, 'data': '', 'ok': 1}
```


