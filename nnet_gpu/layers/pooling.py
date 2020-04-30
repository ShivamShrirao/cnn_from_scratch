#!/usr/bin/env python3
from .base_layer import *
from . import seqinst
from ..stream_handler import stream_maps

class max_pool(Layer):
	def __init__(self,input_shape=None,ksize=[2,2],stride=[2,2],name=None):
		#inp[batches,row,col,channels], kernels[ksz,ksz], stride[row,col]
		super().__init__()
		self.ksz=ksize[0]
		self.param=0
		self.dtype=cp.float32
		self.type=self.__class__.__name__
		if name is None:
			self.name=self.__class__.__name__
		else:
			self.name=name
		if input_shape is None:
			input_shape=seqinst.seq_instance.get_inp_shape()
		self.batches=1
		self.row,self.col,self.channels=input_shape
		# self.rem_col=self.row%self.ksz
		# if self.rem_col:
		# 	self.padded=cp.zeros((self.batches,self.row,self.col,self.channels),dtype=self.dtype)
		self.out_row,self.out_col=self.row//self.ksz,self.col//self.ksz
		# self.row-=self.rem_col
		# self.col-=self.rem_col
		self.shape=(None,self.out_row,self.out_col,self.channels)
		self.mask_stream=stream_maps.get_next_stream()
		self.out_event=stream_maps.default_stream.record()

	def forward(self,inp,training=True):
		self.input_shape=inp.shape
		batches=self.input_shape[0]
		# if self.rem_col:
		# 	inp=inp[:,:-self.rem_col,:-self.rem_col,:]
		# 	if self.batches!=batches:
		# 		self.padded=cp.zeros(self.input_shape,dtype=self.dtype)
		self.batches=batches
		inp=inp.reshape(self.batches,self.out_row,self.ksz,self.out_col,self.ksz,self.channels)
		output=inp.max(axis=(2,4),keepdims=True)
		self.out_event=stream_maps.default_stream.record(self.out_event)
		with self.mask_stream:
			self.mask_stream.wait_event(self.out_event)
			self.mask=(inp==output)
		return output.reshape(self.batches,self.out_row,self.out_col,self.channels)

	def backprop(self,grads,layer=1):
		#grads[self.batches,esz,esz,self.channels],inp[self.batches,row,col,self.channels],kernels[self.ksz,self.ksz],stride[row,col]
		z_out=(self.mask*grads.reshape(self.batches,self.out_row,1,self.out_col,1,self.channels))
		# if self.rem_col:
		# 	self.padded[:,:-self.rem_col,:-self.rem_col,:]=z_out.reshape(self.batches,self.row,self.col,self.channels)
		# 	return self.padded.reshape(self.input_shape)
		# else:
		return z_out.reshape(self.input_shape)

class globalAveragePool(Layer):
	def __init__(self,input_shape=None,name=None):
		super().__init__()
		self.type=self.__class__.__name__
		if name is None:
			self.name=self.__class__.__name__
		else:
			self.name=name
		if input_shape is None:
			input_shape=seqinst.seq_instance.get_inp_shape()
		self.param=0
		self.batches=1
		self.row,self.col,self.channels=input_shape
		self.Ncount=self.row*self.col
		self.shape=(None,self.channels)

	def forward(self,inp,training=True):
		self.input_shape=inp.shape
		self.batches=self.input_shape[0]
		inp=inp.reshape(self.batches,self.Ncount,self.channels)
		output=inp.mean(axis=1)
		return output.reshape(self.batches,self.channels)

	def backprop(self,grads,layer=1):
		# grads/=self.Ncount
		z_out=grads.repeat(self.Ncount,axis=0).reshape(self.batches,self.row,self.col,self.channels)
		return z_out