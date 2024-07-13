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

uniform mat4 p3d_ModelViewProjectionMatrix;
uniform mat3 p3d_NormalMatrix;
uniform mat4 p3d_ModelViewMatrix;

uniform samplerBuffer texbuffer;
uniform samplerBuffer colormap;
uniform float z_scaling;
uniform float colormap_length;

in vec4 p3d_Vertex;
in vec3 p3d_Normal;
in vec2 p3d_MultiTexCoord0;

out vec2 uv;
out vec4 shadow_uv;
out vec3 normal;
out vec3 offset;

out float vertex_z;

uniform int geomtype;

void main(){
    offset = texelFetch(texbuffer, gl_InstanceID).xyz;
    //position
    if (geomtype==1){
        float appliedZPosition = (p3d_Vertex.z > 0.0) ? offset.z : 0.0;
        gl_Position = p3d_ModelViewProjectionMatrix * 
            vec4(p3d_Vertex + vec4(offset.x, offset.y, appliedZPosition * z_scaling, 1));
        vertex_z = appliedZPosition;
    }
    else {
        gl_Position = p3d_ModelViewProjectionMatrix * p3d_Vertex;
        vertex_z = p3d_Vertex.z;
    }
    //normal      
    normal = p3d_NormalMatrix * p3d_Normal;
    //uv
    uv = p3d_MultiTexCoord0;
    //shadows
    shadow_uv = p3d_LightSource[0].shadowViewMatrix * (p3d_ModelViewMatrix * p3d_Vertex);
}