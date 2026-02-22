from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration


def generate_launch_description():
    backend_arg = DeclareLaunchArgument(
        'backend',
        default_value='keyword',
        description='LLM backend: keyword or llama_cpp'
    )

    model_path_arg = DeclareLaunchArgument(
        'model_path',
        default_value='',
        description='Path to GGUF model file (for llama_cpp backend)'
    )

    n_ctx_arg = DeclareLaunchArgument(
        'n_ctx',
        default_value='2048',
        description='Context window size for llama_cpp backend'
    )

    model_name_arg = DeclareLaunchArgument(
        'model_name',
        default_value='qwen2.5-1.5b',
        description='Model config key (e.g. qwen2.5-1.5b, llama3.2-1b)'
    )

    n_threads_arg = DeclareLaunchArgument(
        'n_threads',
        default_value='4',
        description='Number of CPU threads for llama_cpp backend'
    )

    llm_node = Node(
        package='dexi_llm',
        executable='llm_node',
        name='llm_node',
        namespace='dexi/llm',
        parameters=[{
            'backend': LaunchConfiguration('backend'),
            'model_path': LaunchConfiguration('model_path'),
            'model_name': LaunchConfiguration('model_name'),
            'n_ctx': LaunchConfiguration('n_ctx'),
            'n_threads': LaunchConfiguration('n_threads'),
        }],
        output='screen'
    )

    return LaunchDescription([
        backend_arg,
        model_path_arg,
        model_name_arg,
        n_ctx_arg,
        n_threads_arg,
        llm_node,
    ])
