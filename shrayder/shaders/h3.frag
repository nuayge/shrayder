#version 410

uniform struct {
  vec4 position;
  vec3 color;
  vec3 attenuation;
  vec3 spotDirection;
  float spotCosCutoff;
  float spotExponent;
  sampler2DShadow shadowMap;
  mat4 shadowViewMatrix;
} p3d_LightSource[1];


uniform sampler2D p3d_Texture0;
uniform vec3 camera_pos;
uniform float shadow_blur;
uniform float colormap_length;
uniform samplerBuffer colormap;
uniform int geomtype;

in vec2 uv;
in vec3 offset;
in vec4 shadow_uv;
in vec3 normal;

in float vertex_z;
out vec4 color;


float textureProjSoft(sampler2DShadow tex, vec4 uv, float bias, float blur)
    {
    float result = textureProj(tex, uv, bias);
    result += textureProj(tex, vec4(uv.xy + vec2( -0.326212, -0.405805)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(-0.840144, -0.073580)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(-0.695914, 0.457137)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(-0.203345, 0.620716)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(0.962340, -0.194983)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(0.473434, -0.480026)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(0.519456, 0.767022)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(0.185461, -0.893124)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(0.507431, 0.064425)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(0.896420, 0.412458)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(-0.321940, -0.932615)*blur, uv.z-bias, uv.w));
    result += textureProj(tex, vec4(uv.xy + vec2(-0.791559, -0.597705)*blur, uv.z-bias, uv.w));
    return result/13.0;
    }    


void main()
    {
    //base color
    vec3 ambient=vec3(.2, 0.2, 0.2);    
    //texture --> We don't have a texture. TODO: handle this.
    vec4 tex=texture(p3d_Texture0, uv);
    //light
    vec3 light=p3d_LightSource[0].color.rgb*max(dot(normalize(normal),-p3d_LightSource[0].spotDirection), 0.7);
    
    //shadows
    // float shadow = textureProj(3d_LightSource[0].shadowMap,shadow_uv); //meh :|
    float shadow = textureProjSoft(p3d_LightSource[0].shadowMap, shadow_uv, 0.0001, shadow_blur);//yay! :)
    
    //make the shadow brighter
    shadow=0.5+shadow*0.5;
    // Get the base color from our blend function

    if(geomtype==-2) {
        // Floor
        color=vec4(tex.rgb*(light*shadow+ambient), tex.a);
    }
    else {
        vec3 baseColor = vec3(1.0, 1.0, 1.0);
        for (int i = 0; i < colormap_length - 1; i++) {
            vec4 texi = texelFetch(colormap, i);
            vec4 texiplus = texelFetch(colormap, i+1);
                
            if (vertex_z >= texi.w && vertex_z <= texiplus.w) {
                float t = (vertex_z - texi.w) / (texiplus.w - texi.w);
                baseColor = mix(texi.rgb, texiplus.rgb, t);
                break;
            }
    }   
        // Shadows are not projected on the Hexagons. Need to understanc why.
        color = vec4(baseColor * light * shadow*1.5, 1);
    }
}