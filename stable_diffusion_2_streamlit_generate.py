'''
https://github.com/dlebech/stable-diffusion-2-streamlit/blob/main/sd2/generate.py
'''
import datetime
import os
import re
from typing import Literal, Union

import streamlit as st
import torch
from diffusers import (
    StableDiffusionPipeline,
    EulerDiscreteScheduler,
    StableDiffusionImg2ImgPipeline,
)

PIPELINE_NAMES = Literal('text2img','img2img')

@st.cache(allow_output_mutation=True, max_entries=1)
def get_pipeline(
    name: PIPELINE_NAMES,
) -> Union[
    StableDiffusionPipeline,
    StableDiffusionImg2ImgPipeline,
]:
    if name in ['text2img', 'img2img']:
        model_id = 'stabilityai/stable-diffusion-2-1-base'
        scheduler = EulerDiscreteScheduler.from_pretrained(
            model_id,
            subfolder='scheduler',
        )
        pipe = StableDiffusionPipeline.from_pretrained(
            model_id,
            scheduler=scheduler,
            revision='fp16',
            torch_dtype=torch.float16,
        )
        if name == 'img2img':
            pipe = StableDiffusionImg2ImgPipeline(**pipe.components)

        pipe = pipe.to('cuda')
        return pipe


def generate(
        prompt,
        pipeline_name: PIPELINE_NAMES,
        image_input=None,
        negative_prompt=None,
        steps=50,
        width=512,
        height=512,
        guidance_scale=7.5,
):
    """Generates an image based on the given prompt and pipeline name"""
    negative_prompt = negative_prompt if negative_prompt else None
    p = st.progress(0)      # display a progress bar
    callback = lambda step, *_: p.progress(step/steps)

    pipe = get_pipeline(pipeline_name)
    torch.cuda.empty_cache()

    kwargs = dict(
        prompt=prompt,
        negative_prompt=negative_prompt,
        num_inference_steps=steps,
        callback=callback,
        guidance_scale=guidance_scale,
    )
    print('kwargs', kwargs)

    if pipeline_name == 'txt2img':
        kwargs.update(width=width, height=height)
    elif pipeline_name == 'img2img' and image_input:
        kwargs.update(image=image_input)
    else:
        raise Exception(
            f'Cannot generate image for pipeline {pipeline_name} and {prompt}'
        )

    with torch.autocast('cuda'):
        image = pipe(**kwargs).images[0]

    os.makedirs('outputs',exist_ok=True)

    filename = (
        'outputs/'
        + re.sub(r'\s+','_',prompt)[:50]
        + f'_{datetime.datetime.now().timestamp()}'
    )
    image.save(f'{filename}.png')
    with open(f'{filename}.txt','w') as f:
        f.write(prompt)
    return image