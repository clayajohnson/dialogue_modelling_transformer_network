#Function so that one session can be called multiple times. 
#Useful while multiple calls need to be done for embedding. 
import tensorflow as tf
import numpy as np
import os
import asyncio
import websockets
import fire
import json
import traceback


import model, sample, encoder 

tf.logging.set_verbosity(tf.logging.ERROR)

model_name = '500' # name of model folder under gpt2/models
enc = encoder.get_encoder(model_name)
hparams = model.default_hparams()
with open(os.path.join('models', model_name, 'hparams.json')) as f:
    hparams.override_from_dict(json.load(f))

length=200

# lots of hard-coded params
seed=None
nsamples=1
batch_size=1
temperature=1
top_k=40
top_p=0.0

hist_len = 3 # feed the last n messages back into the model for context (its memory)

def gpt2_model():
    with tf.Graph().as_default():
        # input placeholder for [batch, input_tokens]
        context = tf.placeholder(tf.int32, [1, None]) # first dim is batch size (1), second is output text len
        np.random.seed(seed)
        tf.set_random_seed(seed)
        output = sample.sample_sequence(
            hparams=hparams, length=length,
            context=context,
            batch_size=1,
            temperature=temperature, top_k=top_k, top_p=top_p
        )
        saver = tf.train.Saver()
        ckpt = tf.train.latest_checkpoint(os.path.join('models', model_name))
        sess = tf.train.MonitoredSession()
        saver.restore(sess, ckpt)
        return lambda x: sess.run(output, feed_dict={ context: x})[:, len(x[0]):] # len(x[0]) returns everything after input prompt

model_fn = gpt2_model()


import socket
import sys

# HOST = 'localhost'	# Symbolic name, meaning all available interfaces
# PORT = 9999	# Arbitrary non-privileged port

# s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# print(f'Socket created on {HOST}:{PORT}')

# #Bind socket to local host and port
# try:
#     s.bind((HOST, PORT))
# except socket.error as msg:
#     print('Bind failed. Error Code : ' + str(msg[0]) + ' Message ' + msg[1])
#     sys.exit()
#     
# print('Socket bind complete')

# #Start listening on socket
# s.listen(10)
# print('Socket now listening')

hist_buf = []
global auto_text
auto_text = []

async def handle_message(websocket, input_msg):
    global auto_text
    print(input_msg)
    #input_msg = conn.recv(4096).decode("utf-8").strip()
    if input_msg == '':
        if len(auto_text) > 0:
            print('Printing what goes next')
            return_string = auto_text[0]
            await websocket.send(return_string) # send result to client
            hist_buf.append(return_string) # store
            print(hist_buf[-hist_len:])
            del auto_text[0] #use it like a FIFO queue.Because there are two /ns, need to delete the following /2 after something is said.
        else:
            print('Nothing left to say')
            if len(hist_buf) > 0:
                hist = ''.join(hist_buf[-hist_len:])
            else:
                hist = 'Welcome to the Joe Rogan podcast on mars, philosophy and life.'
            context_tokens = enc.encode(hist)
            print('running through gpt2...')
            out_tokens = model_fn([context_tokens]) # passes this to the lambda
            out_str = enc.decode(out_tokens[0])
            split_text = out_str.split('\n')
            
            trunc_text = split_text[0]
            for x in split_text[1:]:
                print(x, x != '\n\n')
                if x!='\n\n':
                    auto_text.append(x)
            print(out_str)
            print(trunc_text)
            return_string = trunc_text
            hist_buf.append(return_string)
            await websocket.send(return_string) # send result to client
            
            
    else:
        auto_text = []
        # if input_msg == 'cc':
        #     conn.close()
        #     print('Connection closed with ' + addr[0] + ':' + str(addr[1]))
        #     break
        print('>>Recvd msg:'+input_msg)
        hist = ''.join(hist_buf[-hist_len:]) # run the last few messages back into the model for context
        context_tokens = enc.encode(hist+"[INPUT]: "+input_msg+"\n\n[Joe Rogan]:")
        print('running through gpt2...')
        out_tokens = model_fn([context_tokens]) # passes this to the lambda
        out_str = enc.decode(out_tokens[0])
        split_text = out_str.split('\n')
        
        trunc_text = split_text[0]
  
        for x in split_text[1:]:
            print(x, x != '\n\n')
            if x!='\n\n':
                auto_text.append(x)
            
        print(out_str)
        print(trunc_text)
        return_string = trunc_text

        #conn.send(return_string.encode('utf-8')) # send result to client

        hist_buf.append("[INPUT]: "+input_msg+"\n\n[Joe Rogan]:"+trunc_text+"\n\n") # store history of convo
        await websocket.send(return_string)

async def consumer_handler(websocket, path):
    while True:
        input_msg = await websocket.recv()
        await handle_message(websocket,input_msg)

start_server = websockets.serve(consumer_handler, 'localhost', '10001')

asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
#now keep talking with the client
# try:
#     while True:
#         #wait to accept a connection - blocking call
#         conn, addr = s.accept()
#         print('Connected with ' + addr[0] + ':' + str(addr[1]))
#         hist_buf = []
#         auto_text = []
#         while True:
#             input_msg = conn.recv(4096).decode("utf-8").strip()
#             if input_msg == '':
#                 if len(auto_text) > 0:
#                     print('Printing what goes next')
#                     return_string = auto_text[0] +'\n\n'
#                     conn.send(return_string.encode('utf-8')) # send result to client
#                     hist_buf.append(return_string) # store
#                     print(hist_buf[-hist_len:])
#                     del auto_text[0] #use it like a FIFO queue.Because there are two /ns, need to delete the following /2 after something is said.
#                 else:
#                     print('Nothing left to say')
#                     if len(hist_buf) > 0:
#                         hist = ''.join(hist_buf[-hist_len:])
#                     else:
#                         hist = 'Welcome to the Joe Rogan podcast on mars, philosophy and life.'
#                     context_tokens = enc.encode(hist)
#                     print('running through gpt2...')
#                     out_tokens = model_fn([context_tokens]) # passes this to the lambda
#                     out_str = enc.decode(out_tokens[0])
#                     split_text = out_str.split('\n')
#                     
#                     trunc_text = split_text[0]
#                     
#                     auto_text = [x for x in split_text[1:] if x != '\n\n']
#                     print(out_str)
#                     print(trunc_text)
#                     return_string = "\nJoe Rogan:"+ trunc_text +'\n\n'

#                     conn.send(return_string.encode('utf-8')) # send result to client
#                     
#                     
#             else:
#                 auto_text = []
#                 if input_msg == 'cc':
#                     conn.close()
#                     print('Connection closed with ' + addr[0] + ':' + str(addr[1]))
#                     break
#                 print('>>Recvd msg:'+input_msg)
#                 hist = ''.join(hist_buf[-hist_len:]) # run the last few messages back into the model for context
#                 context_tokens = enc.encode(hist+"[INPUT]: "+input_msg+"\n\n[Joe Rogan]:")
#                 print('running through gpt2...')
#                 out_tokens = model_fn([context_tokens]) # passes this to the lambda
#                 out_str = enc.decode(out_tokens[0])
#                 split_text = out_str.split('\n')
#                 
#                 trunc_text = split_text[0]
#                 auto_text = [x for x in split_text[1:] if x != '\n\n']
#                 print(out_str)
#                 print(trunc_text)
#                 return_string = "\nJoe Rogan:"+ trunc_text +'\n\n'

#                 conn.send(return_string.encode('utf-8')) # send result to client

#                 hist_buf.append("[INPUT]: "+input_msg+"\n\n[Joe Rogan]:"+trunc_text+"\n\n") # store history of convo
# except Exception as e:
#     print(traceback.format_exc())
#     s.close()
#     
# s.close()
