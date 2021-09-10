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

This will result in URL parse of: "https://<server>:<port>/my_api/next_arg?name=bob&age=50"

